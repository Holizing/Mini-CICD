import os
import subprocess
from pathlib import Path
from typing import Optional
from backend.build.utils import run_command, get_commit_hash, ensure_directory_exists


class BuildRunner:
    def __init__(self, workspace_dir: str, logs_dir: str):
        self.workspace_dir = workspace_dir
        self.logs_dir = logs_dir
        ensure_directory_exists(workspace_dir)
        ensure_directory_exists(logs_dir)

        # Build file detection priority (highest to lowest)
        self.build_files = ['pom.xml', 'build.gradle', 'package.json', 'requirements.txt', 'Dockerfile']

        # Artifact file extensions to detect after build (prioritize these)
        self.artifact_extensions = ['.war', '.jar', '.zip', '.tar.gz', '.tgz']

        # Artifact directories to detect (for Node.js, static sites, etc.)
        # Note: target/classes is NOT an artifact, it's compiled source
        self.artifact_directories = ['build', 'dist', 'out', 'public']

    def _log(self, log_file, message: str) -> None:
        """Write message to log file."""
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"{message}\n")

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

        # Search for build files in the project directory and subdirectories
        for root, dirs, files in os.walk(project_path):
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

        # First, check for artifact files (.war, .jar, .zip, etc.) - HIGHEST PRIORITY
        found_artifacts = []

        for root, dirs, files in os.walk(project_root):
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
                return artifact_path, "file"

            # If multiple artifacts found, prefer the one in target/ (Maven) or build/ (Gradle)
            preferred_dirs = ['target', 'build', 'dist', 'out']
            for preferred_dir in preferred_dirs:
                for artifact_path in found_artifacts:
                    if preferred_dir in artifact_path:
                        self._log(log_file, f"Multiple artifacts found, using preferred directory: {artifact_path}")
                        return artifact_path, "file"

            # Fallback to the first artifact
            artifact_path = found_artifacts[0]
            self._log(log_file, f"Multiple artifacts found, using first: {artifact_path}")
            return artifact_path, "file"

        # Second, check for artifact directories (Node.js build/, dist/, etc.) - FALLBACK
        for artifact_dir in self.artifact_directories:
            dir_path = os.path.join(project_root, artifact_dir)
            if os.path.isdir(dir_path):
                # Check if directory has content
                if os.listdir(dir_path):
                    self._log(log_file, f"Found artifact directory: {dir_path}")
                    return dir_path, "directory"

        self._log(log_file, f"No artifacts found")
        return None, None

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
                self.workspace_dir
            )

            if not success:
                error_msg = f"Git clone failed: {stderr}"
                self._log(log_file, error_msg)
                return False, error_msg

            self._log(log_file, f"Repository cloned successfully")

            # Checkout branch
            success, stdout, stderr = run_command(["git", "checkout", branch], project_path)
            if not success:
                error_msg = f"Git checkout branch {branch} failed: {stderr}"
                self._log(log_file, error_msg)
                return False, error_msg
        else:
            # Pull latest changes
            self._log(log_file, f"Repository exists, pulling latest changes...")

            # Fetch
            success, stdout, stderr = run_command(["git", "fetch"], project_path)
            if not success:
                error_msg = f"Git fetch failed: {stderr}"
                self._log(log_file, error_msg)
                return False, error_msg

            # Checkout branch
            success, stdout, stderr = run_command(["git", "checkout", branch], project_path)
            if not success:
                error_msg = f"Git checkout failed: {stderr}"
                self._log(log_file, error_msg)
                return False, error_msg

            # Pull
            success, stdout, stderr = run_command(
                ["git", "pull", "origin", branch],
                project_path
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
                    timeout=1800  # 30 minutes timeout per command
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
                error_msg = f"Command {i} timed out after 30 minutes: {cmd}"
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
        git_url: str,
        project_name: str,
        branch: str,
        build_id: int,
        build_script: Optional[str] = None
    ) -> tuple[bool, Optional[str], Optional[str], Optional[str], Optional[str]]:
        """
        Execute the complete build pipeline.

        Args:
            git_url: Git repository URL
            project_name: Name of the project
            branch: Git branch to build
            build_id: Build ID for logging
            build_script: Custom build script (optional)

        Returns:
            Tuple of (success: bool, commit_hash: str, error_message: str, artifact_path: str, artifact_type: str)
        """
        log_file = os.path.join(self.logs_dir, f"build_{build_id}.log")
        project_path = os.path.join(self.workspace_dir, project_name)

        self._log(log_file, f"=== Build #{build_id} Started ===")
        self._log(log_file, f"Project: {project_name}")
        self._log(log_file, f"Branch: {branch}")
        self._log(log_file, f"Git URL: {git_url}")

        # Step 1: Clone or Pull
        success, error = self.clone_or_pull(git_url, project_name, branch, log_file)
        if not success:
            return False, None, error, None, None

        # Step 2: Detect project root
        project_root = self.detect_project_root(project_path, log_file)

        # Step 3: Get commit hash
        commit_hash = get_commit_hash(project_path)
        if commit_hash:
            self._log(log_file, f"Current commit: {commit_hash}")
        else:
            self._log(log_file, f"Warning: Could not get commit hash")

        # Step 4: Execute custom build script from project root
        success, error = self.execute_build_script(project_root, build_script, log_file)
        if not success:
            return False, commit_hash, error, None, None

        # Step 5: Detect build artifact
        artifact_path, artifact_type = self.detect_artifact(project_root, log_file)
        if artifact_path:
            self._log(log_file, f"Build artifact detected: {artifact_path} (type: {artifact_type})")

        self._log(log_file, f"=== Build #{build_id} Completed Successfully ===")

        return True, commit_hash, "", artifact_path, artifact_type
