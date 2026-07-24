import os
import subprocess
import time
from pathlib import Path
from typing import Optional, List
from datetime import datetime
from backend.build.utils import run_command, get_commit_hash, ensure_directory_exists
from backend.build.detector import ProjectDetector


class BuildRunner:
    def __init__(
        self,
        workspace_dir: str,
        logs_dir: str,
        db_session=None,
        timeout_seconds: int = 600,
        deadline: Optional[float] = None,
    ):
        self.workspace_dir = workspace_dir
        self.logs_dir = logs_dir
        self.db_session = db_session
        self.timeout_seconds = timeout_seconds
        self.deadline = deadline or (time.monotonic() + timeout_seconds)
        ensure_directory_exists(workspace_dir)
        ensure_directory_exists(logs_dir)

        # Build file detection priority (highest to lowest)
        self.build_files = ['pom.xml', 'build.gradle', 'package.json', 'requirements.txt', 'Dockerfile']

        # Artifact file extensions to detect after build (prioritize these)
        self.artifact_extensions = ['.war', '.jar', '.zip', '.tar.gz', '.tgz']

        # Artifact directories to detect (for Node.js, static sites, etc.)
        # Note: target/classes is NOT an artifact, it's compiled source
        # Note: 'public' is removed because it's typically static files for Express/static sites, not build output
        self.artifact_directories = ['build', 'dist', 'out']

        # Stage tracking
        self.current_build_id = None
        self.stages = {}  # stage_name -> stage_id
        self.stage_logs = {}  # stage_name -> log_file_path

    def _remaining_timeout(self) -> float:
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(
                f"Build timed out after {self.timeout_seconds} seconds"
            )
        return max(0.1, remaining)

    def _log(self, log_file, message: str) -> None:
        """Write message to log file."""
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"{message}\n")

    def _log_stage(self, stage_name: str, message: str) -> None:
        """Write message to stage-specific log file and raw log file."""
        if stage_name in self.stage_logs:
            stage_log_file = self.stage_logs[stage_name]
            with open(stage_log_file, "a", encoding="utf-8") as f:
                f.write(f"{message}\n")

    def _create_stage_log_dir(self, build_id: int) -> str:
        """Create directory for stage logs."""
        stage_log_dir = os.path.join(self.logs_dir, f"build_{build_id}")
        ensure_directory_exists(stage_log_dir)
        return stage_log_dir

    def _create_stage(self, build_id: int, stage_name: str) -> int:
        """Create a new build stage in database and return its ID."""
        if not self.db_session:
            return 0

        from backend.build.models import BuildStage

        stage_log_dir = self._create_stage_log_dir(build_id)
        stage_log_file = os.path.join(stage_log_dir, f"{stage_name.lower().replace(' ', '_')}.log")

        stage = BuildStage(
            build_id=build_id,
            stage_name=stage_name,
            status="pending",
            log_file=stage_log_file
        )

        self.db_session.add(stage)
        self.db_session.commit()
        self.db_session.refresh(stage)

        self.stages[stage_name] = stage.id
        self.stage_logs[stage_name] = stage_log_file

        return stage.id

    def _start_stage(self, stage_name: str) -> None:
        """Mark a stage as running."""
        if not self.db_session or stage_name not in self.stages:
            return

        from backend.build.models import BuildStage

        stage = self.db_session.query(BuildStage).filter(BuildStage.id == self.stages[stage_name]).first()
        if stage:
            stage.status = "running"
            stage.started_at = datetime.utcnow()
            self.db_session.commit()

    def _complete_stage(self, stage_name: str, status: str = "success", error_message: str = None) -> None:
        """Mark a stage as completed (success or failed)."""
        if not self.db_session or stage_name not in self.stages:
            return

        from backend.build.models import BuildStage

        stage = self.db_session.query(BuildStage).filter(BuildStage.id == self.stages[stage_name]).first()
        if stage:
            stage.status = status
            stage.finished_at = datetime.utcnow()
            if stage.started_at:
                stage.duration = int((stage.finished_at - stage.started_at).total_seconds())
            if error_message:
                stage.error_message = error_message
            self.db_session.commit()

    def _load_stages(self, build_id: int) -> bool:
        if not self.db_session:
            return False

        from backend.build.models import BuildStage

        stages = (
            self.db_session.query(BuildStage)
            .filter(BuildStage.build_id == build_id)
            .order_by(BuildStage.id)
            .all()
        )
        if not stages:
            return False

        self.current_build_id = build_id
        self.stages = {stage.stage_name: stage.id for stage in stages}
        self.stage_logs = {
            stage.stage_name: stage.log_file
            for stage in stages
            if stage.log_file
        }
        return True

    def _initialize_stages(self, build_id: int, build_type: str, docker_mode: str = None) -> None:
        """Initialize all stages for a build."""
        if self._load_stages(build_id):
            return

        self.current_build_id = build_id
        self.stages = {}
        self.stage_logs = {}

        # Common stages
        self._create_stage(build_id, "Clone Repository")
        self._create_stage(build_id, "Detect Project Type")

        if build_type == "docker":
            if docker_mode == "existing_image":
                self._create_stage(build_id, "Validate Docker Image")
            else:
                self._create_stage(build_id, "Execute Build Script")
                self._create_stage(build_id, "Build Docker Image")
        else:
            self._create_stage(build_id, "Execute Build Script")
            self._create_stage(build_id, "Detect Artifact")

        self._create_stage(build_id, "Finalize Build")

    def detect_project_root(self, project_path: str, log_file: str) -> str:
        """
        Detect the actual project root by searching for build files.

        Args:
            project_path: Path to the cloned repository
            log_file: Path to log file

        Returns:
            Path to the detected project root (or original path if not found)
        """
        self._log(log_file, f"Detecting project root...")

        found_files = []
        exclude_dirs = {'.git', 'node_modules', 'venv', '__pycache__', 'target', 'build', 'dist', 'coverage', 'vendor'}

        # Search for build files in the project directory and subdirectories
        for root, dirs, files in os.walk(project_path):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            for build_file in self.build_files:
                if build_file in files:
                    found_files.append((root, build_file))
                    self._log(log_file, f"Found {build_file} at {root}")

        if not found_files:
            self._log(log_file, f"No build files found, using repository root: {project_path}")
            return project_path

        # If exactly one build file found, use that directory
        if len(found_files) == 1:
            detected_root = found_files[0][0]
            self._log(log_file, f"Exactly one build file found, using project root: {detected_root}")
            return detected_root

        # If multiple build files found, use the one with highest priority
        # Priority is based on the order in self.build_files
        for priority_file in self.build_files:
            for root, found_file in found_files:
                if found_file == priority_file:
                    detected_root = root
                    self._log(log_file, f"Multiple build files found, using highest priority: {priority_file} at {detected_root}")
                    return detected_root

        # Fallback to repository root
        self._log(log_file, f"Could not determine project root, using repository root: {project_path}")
        return project_path

    def detect_artifact(self, project_root: str, log_file: str) -> tuple[Optional[str], Optional[str]]:
        """
        Detect build artifact (.war, .jar, .zip, etc.) or directory (build/, dist/) in the project.

        Priority: Files (.war, .jar, .zip) > Directories (build/, dist/)

        Args:
            project_root: Path to the project root directory
            log_file: Path to log file

        Returns:
            Tuple of (artifact_path: str, artifact_type: str) or (None, None) if not found
        """
        self._log(log_file, f"Detecting build artifact...")

        # First, specifically check for WAR files in target/ directory (Maven builds)
        target_dir = os.path.join(project_root, 'target')
        if os.path.isdir(target_dir):
            self._log(log_file, f"Checking target directory for WAR files: {target_dir}")
            war_files = []
            for file in os.listdir(target_dir):
                if file.endswith('.war'):
                    war_path = os.path.join(target_dir, file)
                    war_files.append(war_path)
                    self._log(log_file, f"Found WAR file: {war_path}")
            
            if war_files:
                # Sort by modification time, newest first
                war_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                artifact_path = war_files[0]
                self._log(log_file, f"Using newest WAR file: {artifact_path}")
                # Return relative path from workspace_dir
                rel_path = os.path.relpath(artifact_path, self.workspace_dir)
                return rel_path, "war"

        # Exclude directories from artifact search (dependencies, cache, etc.)
        # Note: 'target' is NOT excluded here since we already checked it above
        exclude_dirs = {'.git', 'node_modules', 'venv', '__pycache__', 'build', 'dist', 'coverage', 'vendor', '.next', '.venv', 'tmp', 'cache', 'logs'}

        # First, check for artifact directories (build/, dist/, etc.) - HIGHEST PRIORITY for Node.js/static sites
        for artifact_dir in self.artifact_directories:
            dir_path = os.path.join(project_root, artifact_dir)
            if os.path.isdir(dir_path):
                # Check if directory has content
                if os.listdir(dir_path):
                    self._log(log_file, f"Found artifact directory: {dir_path}")
                    # Return relative path from workspace_dir
                    rel_path = os.path.relpath(dir_path, self.workspace_dir)
                    return rel_path, "directory"

        # Second, check for artifact files (.war, .jar, .zip, etc.) - for Java/other compiled languages
        found_artifacts = []

        for root, dirs, files in os.walk(project_root):
            # Exclude unwanted directories
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                if any(file.endswith(ext) for ext in self.artifact_extensions):
                    artifact_path = os.path.join(root, file)
                    found_artifacts.append(artifact_path)
                    self._log(log_file, f"Found artifact file: {artifact_path}")

        if found_artifacts:
            # If exactly one artifact found, use it
            if len(found_artifacts) == 1:
                artifact_path = found_artifacts[0]
                self._log(log_file, f"Exactly one artifact file found: {artifact_path}")
                # Return relative path from workspace_dir
                rel_path = os.path.relpath(artifact_path, self.workspace_dir)
                # Determine artifact type based on extension
                artifact_type = "war" if artifact_path.endswith('.war') else "file"
                return rel_path, artifact_type

            # If multiple artifacts found, prefer the one in target/ (Maven) or build/ (Gradle)
            preferred_dirs = ['target', 'build', 'dist', 'out']
            for preferred_dir in preferred_dirs:
                for artifact_path in found_artifacts:
                    if preferred_dir in artifact_path:
                        self._log(log_file, f"Multiple artifacts found, using preferred directory: {artifact_path}")
                        # Return relative path from workspace_dir
                        rel_path = os.path.relpath(artifact_path, self.workspace_dir)
                        artifact_type = "war" if artifact_path.endswith('.war') else "file"
                        return rel_path, artifact_type

            # Fallback to the first artifact
            artifact_path = found_artifacts[0]
            self._log(log_file, f"Multiple artifacts found, using first: {artifact_path}")
            # Return relative path from workspace_dir
            rel_path = os.path.relpath(artifact_path, self.workspace_dir)
            artifact_type = "war" if artifact_path.endswith('.war') else "file"
            return rel_path, artifact_type

        self._log(log_file, f"No artifacts found")
        return None, None

    def detect_dockerfile(self, project_path: str, log_file: str) -> Optional[str]:
        """
        Detect Dockerfile in the project.

        Args:
            project_path: Path to the project root directory
            log_file: Path to log file

        Returns:
            Path to Dockerfile or None if not found
        """
        self._log(log_file, "Detecting Dockerfile...")
        
        # First check the repository root directly
        dockerfile_path = os.path.join(project_path, 'Dockerfile')
        if os.path.exists(dockerfile_path):
            self._log(log_file, f"Found Dockerfile at {dockerfile_path}")
            return dockerfile_path
            
        # Then search everywhere
        exclude_dirs = {'.git', 'node_modules', 'venv', '__pycache__', 'target', 'build', 'dist', 'coverage', 'vendor'}
        found = []
        for root, dirs, files in os.walk(project_path):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            if 'Dockerfile' in files:
                found.append(os.path.join(root, 'Dockerfile'))
                
        if found:
            # Prefer the one with the shortest path (closest to root)
            found.sort(key=len)
            best_dockerfile = found[0]
            self._log(log_file, f"Found Dockerfile at {best_dockerfile}")
            return best_dockerfile
            
        self._log(log_file, f"No Dockerfile found")
        return None

    def execute_docker_build(self, project_root: str, image_name: str, image_tag: str, dockerfile_path: str, build_context: str, log_file: str = None) -> tuple[bool, str]:
        """
        Execute docker build command.

        Args:
            project_root: Path to the project root directory
            image_name: Docker image name
            image_tag: Docker image tag
            dockerfile_path: Path to Dockerfile
            build_context: Build context
            log_file: Path to log file

        Returns:
            Tuple of (success: bool, error_message: str)
        """
        # Convert paths to absolute paths
        abs_dockerfile_path = os.path.abspath(dockerfile_path)
        abs_build_context = os.path.abspath(build_context)

        # Verify build context exists
        if not os.path.exists(abs_build_context):
            error_msg = f"Error: Build context path does not exist: {abs_build_context}"
            self._log(log_file, error_msg)
            return False, error_msg

        self._log(log_file, f"Building Docker image: {image_name}:{image_tag}")
        self._log(log_file, f"Detected Dockerfile:\n{abs_dockerfile_path}\n")
        self._log(log_file, f"Build Context:\n{abs_build_context}\n")

        # Build docker command
        docker_cmd = f'docker build -f "{abs_dockerfile_path}" -t {image_name}:{image_tag} "{abs_build_context}"'

        try:
            result = subprocess.run(
                docker_cmd,
                shell=True,
                cwd=abs_build_context,
                capture_output=True,
                text=True,
                timeout=self._remaining_timeout(),
            )

            # Log output
            if result.stdout:
                self._log(log_file, f"STDOUT:\n{result.stdout}")
            if result.stderr:
                self._log(log_file, f"STDERR:\n{result.stderr}")

            # Check if command failed
            if result.returncode != 0:
                error_msg = f"Docker build failed with exit code {result.returncode}"
                if result.stderr:
                    error_msg += f"\nError: {result.stderr}"
                self._log(log_file, error_msg)
                return False, error_msg

            self._log(log_file, f"Docker image built successfully: {image_name}:{image_tag}")
            return True, ""

        except subprocess.TimeoutExpired:
            error_msg = (
                f"Docker build timed out after {self.timeout_seconds} seconds"
            )
            self._log(log_file, error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Docker build failed with exception: {str(e)}"
            self._log(log_file, error_msg)
            return False, error_msg

    def clone_or_pull(self, git_url: str, project_name: str, branch: str, log_file: str) -> tuple[bool, str]:
        """
        Clone repository if not exists, otherwise pull latest changes.

        Returns:
            Tuple of (success: bool, error_message: str)
        """
        project_path = os.path.join(self.workspace_dir, project_name)

        if not os.path.exists(project_path):
            # Clone repository
            self._log(log_file, f"Cloning repository from {git_url}...")
            success, stdout, stderr = run_command(
                ["git", "clone", git_url, project_name],
                self.workspace_dir,
                self._remaining_timeout(),
            )

            if not success:
                error_msg = f"Git clone failed: {stderr}"
                self._log(log_file, error_msg)
                return False, error_msg

            self._log(log_file, f"Repository cloned successfully")

            # Checkout branch
            success, stdout, stderr = run_command(
                ["git", "checkout", branch],
                project_path,
                self._remaining_timeout(),
            )
            if not success:
                error_msg = f"Git checkout branch {branch} failed: {stderr}"
                self._log(log_file, error_msg)
                return False, error_msg
        else:
            # Pull latest changes
            self._log(log_file, f"Repository exists, pulling latest changes...")

            # Fetch
            success, stdout, stderr = run_command(
                ["git", "fetch"],
                project_path,
                self._remaining_timeout(),
            )
            if not success:
                error_msg = f"Git fetch failed: {stderr}"
                self._log(log_file, error_msg)
                return False, error_msg

            # Checkout branch - try direct checkout first, then create from remote if needed
            success, stdout, stderr = run_command(
                ["git", "checkout", branch],
                project_path,
                self._remaining_timeout(),
            )
            if not success:
                # Branch might not exist locally, try to create from remote
                self._log(log_file, f"Local branch {branch} not found, creating from remote...")
                success, stdout, stderr = run_command(
                    ["git", "checkout", "-b", branch, f"origin/{branch}"],
                    project_path,
                    self._remaining_timeout(),
                )
                if not success:
                    error_msg = f"Git checkout failed: {stderr}"
                    self._log(log_file, error_msg)
                    return False, error_msg

            # Pull
            success, stdout, stderr = run_command(
                ["git", "pull", "origin", branch],
                project_path,
                self._remaining_timeout(),
            )
            if not success:
                error_msg = f"Git pull failed: {stderr}"
                self._log(log_file, error_msg)
                return False, error_msg

            self._log(log_file, f"Repository updated successfully")

        return True, ""

    def execute_build_script(self, project_path: str, build_script: Optional[str], log_file: str) -> tuple[bool, str]:
        """
        Execute custom build script line by line.

        Args:
            project_path: Path to the project directory
            build_script: Custom build script (multiline string)
            log_file: Path to log file

        Returns:
            Tuple of (success: bool, error_message: str)
        """
        if not build_script:
            self._log(log_file, f"No build script provided, skipping build steps")
            return True, ""

        self._log(log_file, f"Executing custom build script...")
        self._log(log_file, f"Build script:\n{build_script}")

        # Split script into commands (one per line)
        commands = [cmd.strip() for cmd in build_script.splitlines() if cmd.strip()]

        for i, cmd in enumerate(commands, 1):
            self._log(log_file, f"\n=== Executing Command {i}/{len(commands)} ===")
            self._log(log_file, f"Command: {cmd}")

            # Execute command in project directory
            try:
                # Use shell=True to support complex commands with pipes, redirects, etc.
                result = subprocess.run(
                    cmd,
                    shell=True,
                    cwd=project_path,
                    capture_output=True,
                    text=True,
                    timeout=self._remaining_timeout(),
                )

                # Log output
                if result.stdout:
                    self._log(log_file, f"STDOUT:\n{result.stdout}")
                if result.stderr:
                    self._log(log_file, f"STDERR:\n{result.stderr}")

                # Check if command failed
                if result.returncode != 0:
                    error_msg = f"Command {i} failed with exit code {result.returncode}: {cmd}"
                    if result.stderr:
                        error_msg += f"\nError: {result.stderr}"
                    self._log(log_file, error_msg)
                    return False, error_msg

                self._log(log_file, f"Command {i} completed successfully")

            except subprocess.TimeoutExpired:
                error_msg = (
                    f"Command {i} timed out after "
                    f"{self.timeout_seconds} seconds: {cmd}"
                )
                self._log(log_file, error_msg)
                return False, error_msg
            except Exception as e:
                error_msg = f"Command {i} failed with exception: {cmd}\nError: {str(e)}"
                self._log(log_file, error_msg)
                return False, error_msg

        self._log(log_file, f"All build commands completed successfully")
        return True, ""

    def execute_build(
        self,
        git_url: Optional[str],
        project_name: str,
        branch: Optional[str],
        build_id: int,
        build_script: Optional[str] = None,
        build_type: str = "source",
        docker_mode: Optional[str] = "build_from_git",
        image_name: Optional[str] = None,
        image_tag: Optional[str] = "latest",
        dockerfile_path: Optional[str] = "./Dockerfile",
        build_context: Optional[str] = ".",
        docker_image: Optional[str] = None,
        docker_compose_file: Optional[str] = None
    ) -> tuple[bool, Optional[str], Optional[str], Optional[str], Optional[str], dict]:
        """
        Execute the complete build pipeline.

        Args:
            git_url: Git repository URL (optional for existing docker image mode)
            project_name: Name of the project
            branch: Git branch to build (optional for existing docker image mode)
            build_id: Build ID for logging
            build_script: Custom build script (optional)
            build_type: Build type (source or docker)
            docker_mode: Docker mode (build_from_git, existing_image)
            image_name: Docker image name (for docker build)
            image_tag: Docker image tag (for docker build)
            dockerfile_path: Path to Dockerfile (for docker build)
            build_context: Build context (for docker build)
            docker_image: Full docker image name with tag (for existing image mode)
            docker_compose_file: Docker Compose file (for existing image mode)

        Returns:
            Tuple of (success: bool, commit_hash: str, error_message: str, artifact_path: str, artifact_type: str)
        """
        log_file = os.path.join(self.logs_dir, f"build_{build_id}.log")
        project_path = os.path.join(self.workspace_dir, project_name)

        # Initialize stages
        self._initialize_stages(build_id, build_type, docker_mode)

        self._log(log_file, f"=== Build #{build_id} Started ===")
        self._log(log_file, f"Project: {project_name}")
        self._log(log_file, f"Build Type: {build_type}")
        if docker_mode:
            self._log(log_file, f"Docker Mode: {docker_mode}")

        # Handle existing docker image mode (no git clone, no build)
        if build_type == "docker" and docker_mode == "existing_image":
            self._log(log_file, f"Existing Docker Image mode - skipping git clone and build")

            # Skip clone stage
            self._start_stage("Clone Repository")
            self._log_stage("Clone Repository", "Skipping git clone for existing docker image mode")
            self._complete_stage("Clone Repository", "success")

            # Skip detect project type
            self._start_stage("Detect Project Type")
            self._log_stage("Detect Project Type", "Skipping project detection for existing docker image mode")
            self._complete_stage("Detect Project Type", "success")

            # Validate docker image
            self._start_stage("Validate Docker Image")
            self._log_stage("Validate Docker Image", f"Validating Docker image: {docker_image}")

            if not docker_image:
                error_msg = "Error: docker_image is required for existing_image mode"
                self._log(log_file, error_msg)
                self._log_stage("Validate Docker Image", error_msg)
                self._complete_stage("Validate Docker Image", "failed", error_msg)
                return False, None, error_msg, None, None, {}

            self._log_stage("Validate Docker Image", f"Docker image validated: {docker_image}")
            self._complete_stage("Validate Docker Image", "success")

            self._log(log_file, f"Using existing Docker image: {docker_image}")

            # Docker image as artifact
            artifact_path = docker_image
            artifact_type = "docker_image"
            self._log(log_file, f"Docker image artifact: {artifact_path}")

            # Finalize build
            self._start_stage("Finalize Build")
            self._log_stage("Finalize Build", f"Build completed successfully with artifact: {artifact_path}")
            self._complete_stage("Finalize Build", "success")

            # Return success with docker image as artifact
            self._log(log_file, f"=== Build #{build_id} Completed Successfully ===")
            return True, None, None, artifact_path, artifact_type, {}

        self._log(log_file, f"Branch: {branch}")
        self._log(log_file, f"Git URL: {git_url}")

        # Step 1: Clone or Pull
        self._start_stage("Clone Repository")
        self._log_stage("Clone Repository", f"Cloning repository from {git_url}...")
        success, error = self.clone_or_pull(git_url, project_name, branch, log_file)
        if not success:
            self._log_stage("Clone Repository", f"Clone failed: {error}")
            self._complete_stage("Clone Repository", "failed", error)
            return False, None, error, None, None, {}
        else:
            self._log_stage("Clone Repository", "Repository cloned successfully")
            self._complete_stage("Clone Repository", "success")

        # Step 2: Detect project root
        self._start_stage("Detect Project Type")
        self._log_stage("Detect Project Type", "Detecting project type and root...")
        project_root = self.detect_project_root(project_path, log_file)
        self._log_stage("Detect Project Type", f"Project root detected: {project_root}")
        self._complete_stage("Detect Project Type", "success")

        # Step 3: Get commit hash
        commit_hash = get_commit_hash(
            project_path,
            self._remaining_timeout(),
        )
        if commit_hash:
            self._log(log_file, f"Current commit: {commit_hash}")
        else:
            self._log(log_file, f"Warning: Could not get commit hash")

        # Step 4: Execute build based on build type
        if build_type == "docker" and not build_script:
            # Auto docker build if no custom script
            self._log(log_file, f"Auto Docker build mode")

            # Execute Build Script stage (for docker build)
            self._start_stage("Execute Build Script")
            self._log_stage("Execute Build Script", "Skipping custom build script for auto docker build")
            self._complete_stage("Execute Build Script", "success")

            # Build Docker Image stage
            self._start_stage("Build Docker Image")
            self._log_stage("Build Docker Image", "Building Docker image...")

            detected_dockerfile = self.detect_dockerfile(project_path, log_file)
            if not detected_dockerfile:
                error_msg = "Error: No Dockerfile found. Cannot proceed with Docker build."
                self._log(log_file, error_msg)
                self._log_stage("Build Docker Image", error_msg)
                self._complete_stage("Build Docker Image", "failed", error_msg)
                return False, commit_hash, error_msg, None, None, {}

            actual_build_context = os.path.dirname(detected_dockerfile)

            # Use provided image name/tag or defaults
            if not image_name:
                image_name = project_name.lower().replace(" ", "-")
            if not image_tag:
                image_tag = "latest"

            success, error = self.execute_docker_build(
                project_root,
                image_name,
                image_tag,
                detected_dockerfile,
                actual_build_context,
                log_file
            )
            if not success:
                self._log_stage("Build Docker Image", f"Docker build failed: {error}")
                self._complete_stage("Build Docker Image", "failed", error)
                return False, commit_hash, error, None, None, {}
            else:
                self._log_stage("Build Docker Image", f"Docker image built successfully: {image_name}:{image_tag}")
                self._complete_stage("Build Docker Image", "success")

            # Docker image as artifact
            artifact_path = f"{image_name}:{image_tag}"
            artifact_type = "docker_image"
            self._log(log_file, f"Docker image artifact: {artifact_path}")
        else:
            # Execute custom build script from project root
            self._start_stage("Execute Build Script")
            self._log_stage("Execute Build Script", "Executing custom build script...")
            success, error = self.execute_build_script(project_root, build_script, log_file)
            if not success:
                self._log_stage("Execute Build Script", f"Build script failed: {error}")
                self._complete_stage("Execute Build Script", "failed", error)
                return False, commit_hash, error, None, None, {}
            else:
                self._log_stage("Execute Build Script", "Build script completed successfully")
                self._complete_stage("Execute Build Script", "success")

            # Step 5: Detect build artifact
            self._start_stage("Detect Artifact")
            self._log_stage("Detect Artifact", "Detecting build artifact...")
            artifact_path, artifact_type = self.detect_artifact(project_root, log_file)
            if artifact_path:
                self._log(log_file, f"Build artifact detected: {artifact_path} (type: {artifact_type})")
                self._log_stage("Detect Artifact", f"Artifact detected: {artifact_path} (type: {artifact_type})")
            else:
                # If no artifact found, use project root as artifact (for source deployment)
                self._log(log_file, f"No build artifact found, using project root for source deployment")
                rel_path = os.path.relpath(project_root, self.workspace_dir)
                artifact_path = rel_path
                artifact_type = "directory"
                self._log_stage("Detect Artifact", f"Using project root as artifact: {artifact_path}")
                self._log(log_file, f"WARNING: No WAR/JAR artifact found. Please ensure the build completed successfully.")
            self._complete_stage("Detect Artifact", "success")

        # Step 6: Run project detection for deployment recommendations
        detection_result = {}
        try:
            detector = ProjectDetector(project_root)
            result = detector.detect()

            if result and result.confidence > 0.5:
                self._log(log_file, f"\n=== Detected Project ===")
                if result.framework:
                    self._log(log_file, f"Framework\n{result.framework}")
                if result.runtime:
                    self._log(log_file, f"Runtime\n{result.runtime}")
                if result.build_tool:
                    self._log(log_file, f"Build Tool\n{result.build_tool}")
                if result.packaging:
                    self._log(log_file, f"Packaging\n{result.packaging}")
                
                detection_result = {
                    'framework': result.framework,
                    'runtime': result.runtime,
                    'build_tool': result.build_tool,
                    'packaging': result.packaging,
                    'recommended_deploy_script': result.recommended_deploy_script,
                    'recommended_deploy_path': result.recommended_deploy_path,
                    'recommended_service_name': result.recommended_service_name,
                    'confidence': result.confidence
                }
            else:
                self._log(log_file, f"\nProject detection completed with low confidence, skipping recommendations")
        except Exception as e:
            self._log(log_file, f"Project detection failed: {str(e)}")

        # Finalize build stage
        self._start_stage("Finalize Build")
        self._log_stage("Finalize Build", f"Build completed successfully with artifact: {artifact_path}")
        self._complete_stage("Finalize Build", "success")

        self._log(log_file, f"=== Build #{build_id} Completed Successfully ===")

        return True, commit_hash, "", artifact_path, artifact_type, detection_result
