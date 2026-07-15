import os
import time
import threading
import subprocess
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from backend.deploy.models import Deploy
from backend.deploy.schemas import DeployStartRequest, DeployResponse
from backend.deploy.ssh import SSHClient
from backend.deploy.utils import get_log_path


class DeployService:
    def __init__(self, db: Session, logs_dir: str, workspace_dir: str = "workspace"):
        self.db = db
        self.logs_dir = logs_dir
        self.workspace_dir = workspace_dir

        # Stage tracking
        self.current_deploy_id = None
        self.stages = {}  # stage_name -> stage_id
        self.stage_logs = {}  # stage_name -> log_file_path

    def _log_stage(self, stage_name: str, message: str) -> None:
        """Write message to stage-specific log file."""
        if stage_name in self.stage_logs:
            stage_log_file = self.stage_logs[stage_name]
            with open(stage_log_file, "a", encoding="utf-8") as f:
                f.write(f"{message}\n")

    def _create_stage_log_dir(self, deploy_id: int) -> str:
        """Create directory for stage logs."""
        stage_log_dir = os.path.join(self.logs_dir, f"deploy_{deploy_id}")
        os.makedirs(stage_log_dir, exist_ok=True)
        return stage_log_dir

    def _create_stage(self, deploy_id: int, stage_name: str) -> int:
        """Create a new deploy stage in database and return its ID."""
        from backend.deploy.models import DeployStage

        stage_log_dir = self._create_stage_log_dir(deploy_id)
        stage_log_file = os.path.join(stage_log_dir, f"{stage_name.lower().replace(' ', '_')}.log")

        stage = DeployStage(
            deploy_id=deploy_id,
            stage_name=stage_name,
            status="pending",
            log_file=stage_log_file
        )

        self.db.add(stage)
        self.db.commit()
        self.db.refresh(stage)

        self.stages[stage_name] = stage.id
        self.stage_logs[stage_name] = stage_log_file

        return stage.id

    def _start_stage(self, stage_name: str) -> None:
        """Mark a stage as running."""
        if stage_name not in self.stages:
            return

        from backend.deploy.models import DeployStage

        stage = self.db.query(DeployStage).filter(DeployStage.id == self.stages[stage_name]).first()
        if stage:
            stage.status = "running"
            stage.started_at = datetime.utcnow()
            self.db.commit()

    def _complete_stage(self, stage_name: str, status: str = "success", error_message: str = None) -> None:
        """Mark a stage as completed (success or failed)."""
        if stage_name not in self.stages:
            return

        from backend.deploy.models import DeployStage

        stage = self.db.query(DeployStage).filter(DeployStage.id == self.stages[stage_name]).first()
        if stage:
            stage.status = status
            stage.finished_at = datetime.utcnow()
            if stage.started_at:
                stage.duration = int((stage.finished_at - stage.started_at).total_seconds())
            if error_message:
                stage.error_message = error_message
            self.db.commit()

    def _initialize_stages(self, deploy_id: int, deploy_type: str, docker_mode: str = None) -> None:
        """Initialize all stages for a deploy."""
        self.current_deploy_id = deploy_id
        self.stages = {}
        self.stage_logs = {}

        # Common stages
        self._create_stage(deploy_id, "Validate Build")
        self._create_stage(deploy_id, "Connect to Server")

        if deploy_type == "docker":
            if docker_mode == "existing_image":
                self._create_stage(deploy_id, "Pull Docker Image")
            else:
                self._create_stage(deploy_id, "Transfer Docker Image")
            self._create_stage(deploy_id, "Run Docker Container")
        else:
            self._create_stage(deploy_id, "Upload Artifact")
            self._create_stage(deploy_id, "Execute Deploy Script")

        self._create_stage(deploy_id, "Finalize Deploy")

    def start_deploy(self, request: DeployStartRequest) -> DeployResponse:
        """
        Start a new deploy process.
        
        Args:
            request: Deploy start request with deploy details
            
        Returns:
            Deploy response with deploy details
        """
        # Verify build exists and is successful
        from backend.build.models import Build
        build = self.db.query(Build).filter(Build.id == request.build_id).first()
        if not build:
            raise ValueError(f"Build {request.build_id} not found")
        if build.status != "success":
            raise ValueError(f"Build {request.build_id} is not successful. Current status: {build.status}")

        # Validate deploy type specific fields
        if request.deploy_type == "docker":
            if not request.container_name:
                raise ValueError("container_name is required for Docker deploy")
            # Validate based on docker mode
            if request.docker_mode == "existing_image":
                if not request.docker_image:
                    raise ValueError("docker_image is required for existing_image mode")
            else:
                # build_from_git mode requires image_name and image_tag from build
                if not build.image_name or not build.image_tag:
                    raise ValueError("Docker deploy requires a Docker build with image_name and image_tag for build_from_git mode")
        else:
            if not request.deploy_path:
                raise ValueError("deploy_path is required for source deploy")
            if not request.service_name:
                raise ValueError("service_name is required for source deploy")

        # Create deploy record
        deploy = Deploy(
            build_id=request.build_id,
            project_id=request.project_id,
            project_name=request.project_name,
            branch=request.branch,
            server_ip=request.server_ip,
            server_user=request.server_user,
            deploy_path=request.deploy_path,
            service_name=request.service_name,
            deploy_type=request.deploy_type,
            deploy_script=request.deploy_script,
            docker_mode=request.docker_mode,
            container_name=request.container_name,
            port_mapping=request.port_mapping,
            docker_image=request.docker_image,
            docker_compose_file=request.docker_compose_file,
            # Get Image Name and Tag from build record for Docker deploy (build_from_git mode)
            image_name=build.image_name if build else None,
            image_tag=build.image_tag if build else None,
            status="running",
            log_path=get_log_path(self.logs_dir, 0)  # Temporary, will update after getting ID
        )
        
        self.db.add(deploy)
        self.db.commit()
        self.db.refresh(deploy)

        # Update log path with actual deploy ID
        deploy.log_path = get_log_path(self.logs_dir, deploy.id)
        self.db.commit()

        # Initialize stages
        self._initialize_stages(deploy.id, request.deploy_type, request.docker_mode)

        # Log start
        self._log(deploy.log_path, f"=== Deploy #{deploy.id} Started ===")
        self._log(deploy.log_path, f"Build ID: {request.build_id}")
        self._log(deploy.log_path, f"Project: {request.project_name}")
        self._log(deploy.log_path, f"Branch: {request.branch}")
        self._log(deploy.log_path, f"Server: {request.server_user}@{request.server_ip}")
        self._log(deploy.log_path, f"Deploy Type: {request.deploy_type}")
        if request.deploy_type == "docker":
            self._log(deploy.log_path, f"Docker Mode: {request.docker_mode}")
            self._log(deploy.log_path, f"Container: {request.container_name}")
            if request.docker_mode == "existing_image":
                self._log(deploy.log_path, f"Docker Image: {request.docker_image}")
            else:
                self._log(deploy.log_path, f"Image: {build.image_name}:{build.image_tag}")
            if request.port_mapping:
                self._log(deploy.log_path, f"Port Mapping: {request.port_mapping}")
        else:
            self._log(deploy.log_path, f"Deploy Path: {request.deploy_path}")
            self._log(deploy.log_path, f"Service: {request.service_name}")

        # Execute deploy in background thread
        thread = threading.Thread(target=self._execute_deploy_sync, args=(deploy, request))
        thread.daemon = True
        thread.start()

        # Return immediately with deploy_id
        return self._deploy_to_response(deploy)

    def _execute_deploy_sync(self, deploy: Deploy, request: DeployStartRequest) -> None:
        """
        Execute deploy synchronously.

        Args:
            deploy: Deploy model instance
            request: Deploy start request
        """
        start_time = time.time()
        log_file = deploy.log_path

        try:
            # Validate Build stage
            self._start_stage("Validate Build")
            self._log_stage("Validate Build", f"Validating build #{request.build_id}...")
            self._log(log_file, f"Step 1: Getting build record...")
            # Get build record to get artifact path - create new session for background thread
            from backend.build.models import Build
            from backend.common.database import SessionLocal
            db_thread = SessionLocal()
            try:
                build = db_thread.query(Build).filter(Build.id == request.build_id).first()
                if build:
                    self._log(log_file, f"Build record found: artifact_path={build.artifact_path}, artifact_type={build.artifact_type}")
                    self._log_stage("Validate Build", f"Build validated: artifact_path={build.artifact_path}, artifact_type={build.artifact_type}")
                else:
                    self._log(log_file, f"Warning: Build record not found")
                    self._log_stage("Validate Build", "Warning: Build record not found")
            finally:
                db_thread.close()
            self._complete_stage("Validate Build", "success")

            # Connect to Server stage
            self._start_stage("Connect to Server")
            self._log_stage("Connect to Server", f"Initializing SSH client for {request.server_user}@{request.server_ip}...")
            self._log(log_file, f"Step 2: Initializing SSH client...")
            self._log(log_file, f"Step 2: Host: {request.server_ip}, User: {request.server_user}")
            self._log(log_file, f"Step 2: Using password: {'Yes' if request.server_password else 'No'}")
            self._log(log_file, f"Step 2: Using SSH key: {'Yes' if request.server_ssh_key else 'No'}")
            # Initialize SSH client
            ssh = SSHClient(
                host=request.server_ip,
                username=request.server_user,
                password=request.server_password,
                key=request.server_ssh_key
            )

            self._log(log_file, f"Step 3: Connecting to SSH server {request.server_user}@{request.server_ip}...")
            self._log_stage("Connect to Server", f"Connecting to SSH server...")
            # Connect to server
            self._log(log_file, f"Step 3: Attempting SSH connection (timeout=60s)...")
            success, error = ssh.connect()
            if not success:
                self._log(log_file, f"Step 3: SSH connection failed: {error}")
                self._log_stage("Connect to Server", f"SSH connection failed: {error}")
                self._complete_stage("Connect to Server", "failed", error)
                raise Exception(error)
            self._log(log_file, f"Step 3: SSH connection established successfully")
            self._log_stage("Connect to Server", "SSH connection established successfully")
            self._complete_stage("Connect to Server", "success")

            if request.deploy_type == "docker":
                self._execute_docker_deploy(ssh, deploy, request, build, log_file)
            else:
                self._execute_source_deploy(ssh, deploy, request, build, log_file)

            self._log(log_file, f"Step 7: Closing SSH connection...")
            # Close SSH connection
            ssh.close()
            self._log(log_file, f"Step 7: SSH connection closed")

            # Finalize Deploy stage
            self._start_stage("Finalize Deploy")
            self._log_stage("Finalize Deploy", "Updating deploy record...")
            self._log(log_file, f"Step 8: Updating deploy record...")
            # Update deploy record as success - use new session for background thread
            end_time = datetime.utcnow()
            duration = int(time.time() - start_time)

            db_update = SessionLocal()
            try:
                deploy_update = db_update.query(Deploy).filter(Deploy.id == deploy.id).first()
                if deploy_update:
                    deploy_update.status = "success"
                    deploy_update.end_time = end_time
                    deploy_update.duration = duration
                    db_update.commit()
                    self._log(log_file, f"Step 8: Deploy record updated successfully")
                    self._log(log_file, f"=== Deploy #{deploy.id} Completed Successfully in {duration}s ===")
                    self._log_stage("Finalize Deploy", f"Deploy completed successfully in {duration}s")
            finally:
                db_update.close()
            self._complete_stage("Finalize Deploy", "success")

        except Exception as e:
            # Handle errors - use new session for background thread
            end_time = datetime.utcnow()
            duration = int(time.time() - start_time)

            db_update = SessionLocal()
            try:
                deploy_update = db_update.query(Deploy).filter(Deploy.id == deploy.id).first()
                if deploy_update:
                    deploy_update.status = "failed"
                    deploy_update.end_time = end_time
                    deploy_update.duration = duration
                    deploy_update.error_message = str(e)
                    db_update.commit()
                    self._log(log_file, f"=== Deploy #{deploy.id} Failed after {duration}s ===")
                    self._log(log_file, f"Error: {str(e)}")
            finally:
                db_update.close()

    def _execute_source_deploy(
        self,
        ssh: SSHClient,
        deploy: Deploy,
        request: DeployStartRequest,
        build,
        log_file: str
    ) -> None:
        """Execute source-based deployment using strategy-based approach."""
        from backend.deploy.strategies import get_strategy, DeploymentContext

        # Upload Artifact stage
        self._start_stage("Upload Artifact")
        self._log_stage("Upload Artifact", "Uploading artifact to remote server...")

        # Check if custom deploy script is provided
        if request.deploy_script:
            self._log(log_file, f"Step 4: Using custom deploy script, skipping strategy-based deployment")
            if build and build.artifact_path and build.artifact_type != "docker_image":
                self._log(log_file, f"Step 4: Uploading artifact...")
                artifact_type = build.artifact_type or "file"
                self._upload_artifact(
                    ssh, build.artifact_path, artifact_type,
                    request.deploy_path, request.service_name, log_file
                )
                self._log(log_file, f"Step 4: Artifact upload completed")
                self._log_stage("Upload Artifact", "Artifact uploaded successfully")
            else:
                self._log_stage("Upload Artifact", "No artifact to upload for custom script mode")
            self._complete_stage("Upload Artifact", "success")

            # Execute Deploy Script stage
            self._start_stage("Execute Deploy Script")
            self._log_stage("Execute Deploy Script", "Executing custom deploy script...")
            self._log(log_file, f"Step 5: Executing custom deploy script...")
            self._execute_custom_script(ssh, request.deploy_script, request.deploy_path, log_file)
            self._log(log_file, f"Step 5: Custom deploy script execution completed")
            self._log_stage("Execute Deploy Script", "Custom deploy script executed successfully")
            self._complete_stage("Execute Deploy Script", "success")
            return

        # Use strategy-based deployment
        self._log(log_file, f"Step 4: Using strategy-based deployment")

        # Get detected framework and runtime from build metadata
        framework = build.detected_framework if build else None
        runtime = build.detected_runtime if build else None

        self._log(log_file, f"Detected Framework: {framework}")
        self._log(log_file, f"Detected Runtime: {runtime}")

        # Get appropriate deployment strategy
        strategy = get_strategy(framework, runtime)

        if strategy:
            self._log(log_file, f"Using deployment strategy: {strategy.name}")

            # Convert relative artifact_path to absolute path
            artifact_path = None
            if build and build.artifact_path:
                artifact_path = build.artifact_path
                # If artifact_path is relative, convert to absolute path using workspace_dir
                if not os.path.isabs(artifact_path):
                    artifact_path = os.path.join(self.workspace_dir, artifact_path)
                    self._log(log_file, f"Converted artifact path to absolute: {artifact_path}")

            # Create deployment context
            context = DeploymentContext(
                ssh_client=ssh,
                deploy_path=request.deploy_path,
                service_name=request.service_name,
                artifact_path=artifact_path,
                artifact_type=build.artifact_type if build else None,
                project_name=build.project_name if build else None,
                additional_params={'framework': framework}
            )

            # Execute strategy
            success = strategy.execute(context, lambda msg: self._log(log_file, msg))

            if success:
                self._log(log_file, f"Step 4: Strategy-based deployment completed successfully")
                self._log_stage("Upload Artifact", "Artifact uploaded successfully via strategy")
                self._complete_stage("Upload Artifact", "success")

                # Perform post-deployment validation
                self._log(log_file, f"Step 5: Validating deployment...")
                validation_success = strategy.validate(context, lambda msg: self._log(log_file, msg))

                if validation_success:
                    self._log(log_file, f"Step 5: Deployment validation passed")
                else:
                    self._log(log_file, f"Step 5: Deployment validation failed")
                    raise Exception("Deployment validation failed")
            else:
                self._log(log_file, f"Step 4: Strategy-based deployment failed")
                raise Exception("Strategy-based deployment failed")
        else:
            self._log(log_file, f"No suitable deployment strategy found for framework={framework}, runtime={runtime}")
            self._log(log_file, f"Falling back to default deployment")

            # Fallback to default deployment
            if build and build.artifact_path and build.artifact_type != "docker_image":
                self._log(log_file, f"Step 4: Uploading artifact...")
                artifact_type = build.artifact_type or "file"
                self._upload_artifact(
                    ssh, build.artifact_path, artifact_type,
                    request.deploy_path, request.service_name, log_file
                )
                self._log(log_file, f"Step 4: Artifact upload completed")
                self._log_stage("Upload Artifact", "Artifact uploaded successfully (fallback)")
            else:
                self._log_stage("Upload Artifact", "No artifact to upload (fallback)")
            self._complete_stage("Upload Artifact", "success")

            # Execute Deploy Script stage (fallback)
            self._start_stage("Execute Deploy Script")
            self._log_stage("Execute Deploy Script", "Executing default deployment...")
            self._execute_default_deployment(ssh, request, log_file)
            self._log_stage("Execute Deploy Script", "Default deployment completed")
            self._complete_stage("Execute Deploy Script", "success")

    def _execute_docker_deploy(
        self,
        ssh: SSHClient,
        deploy: Deploy,
        request: DeployStartRequest,
        build,
        log_file: str
    ) -> None:
        """Execute Docker-based deployment (save/load image + run container OR pull existing image)."""

        # Handle existing docker image mode
        if request.docker_mode == "existing_image":
            docker_image = request.docker_image
            self._start_stage("Pull Docker Image")
            self._log_stage("Pull Docker Image", f"Pulling Docker image {docker_image} from registry...")
            self._log(log_file, f"Step 4: Pulling Docker image {docker_image} from registry...")
            self._pull_docker_image(ssh, docker_image, log_file)
            self._log(log_file, f"Step 4: Docker image pulled successfully")
            self._log_stage("Pull Docker Image", f"Docker image pulled successfully: {docker_image}")
            self._complete_stage("Pull Docker Image", "success")
            full_image = docker_image
        else:
            # build_from_git mode - transfer image from local build
            image_name = deploy.image_name
            image_tag = deploy.image_tag or "latest"
            full_image = f"{image_name}:{image_tag}"

            self._start_stage("Transfer Docker Image")
            self._log_stage("Transfer Docker Image", f"Transferring Docker image {full_image} to remote server...")
            self._log(log_file, f"Step 4: Transferring Docker image {full_image} to remote server...")
            self._transfer_docker_image(ssh, full_image, deploy.id, log_file)
            self._log(log_file, f"Step 4: Docker image transferred successfully")
            self._log_stage("Transfer Docker Image", f"Docker image transferred successfully")
            self._complete_stage("Transfer Docker Image", "success")

        # Run Docker Container stage
        self._start_stage("Run Docker Container")
        self._log_stage("Run Docker Container", "Deploying Docker container...")
        self._log(log_file, f"Step 5: Deploying Docker container...")
        if request.deploy_script:
            self._execute_custom_script(ssh, request.deploy_script, None, log_file)
        else:
            self._run_docker_container(ssh, request, deploy, log_file, full_image)
        self._log(log_file, f"Step 5: Docker deployment completed")
        self._log_stage("Run Docker Container", "Docker container deployed successfully")
        self._complete_stage("Run Docker Container", "success")

        self._log(log_file, f"Step 6: Validating Docker deployment...")
        container_name = request.container_name
        
        # Check if container is running
        self._log(log_file, f"Validating container {container_name}...")
        success, stdout, stderr = ssh.execute_command(
            f"docker ps --filter name=^{container_name}$ --format '{{{{.Names}}}} {{{{.Status}}}}'"
        )
        if success and stdout.strip():
            self._log(log_file, f"✓ Container running: {stdout.strip()}")
        else:
            self._log(log_file, f"✗ Container not running")
            self._log(log_file, f"  stdout: {stdout}")
            self._log(log_file, f"  stderr: {stderr}")
            raise Exception(f"Container {container_name} is not running")
        
        # Check container health status if available
        self._log(log_file, f"Validating container health status...")
        success, stdout, stderr = ssh.execute_command(
            f"docker inspect --format='{{{{.State.Health.Status}}}}' {container_name} 2>/dev/null || echo 'no-healthcheck'"
        )
        if success and stdout.strip() and stdout.strip() != "no-healthcheck":
            health_status = stdout.strip()
            if health_status == "healthy":
                self._log(log_file, f"✓ Container health: {health_status}")
            elif health_status == "starting":
                self._log(log_file, f"⚠ Container health: {health_status}")
            else:
                self._log(log_file, f"✗ Container health: {health_status}")
                self._log(log_file, f"  Container may not be healthy")
        else:
            self._log(log_file, f"✓ No health check configured")
        
        self._log(log_file, f"Step 6: Docker deployment validation passed")

    def _transfer_docker_image(
        self,
        ssh: SSHClient,
        full_image: str,
        deploy_id: int,
        log_file: str
    ) -> None:
        """
        Export Docker image locally, upload via SFTP, and load on remote server.
        """
        local_tar = os.path.join(self.logs_dir, f"docker_image_{deploy_id}.tar")
        remote_tar = f"/tmp/docker_image_{deploy_id}.tar"

        self._log(log_file, f"Saving Docker image locally: {full_image}")
        try:
            result = subprocess.run(
                ["docker", "save", "-o", local_tar, full_image],
                capture_output=True,
                text=True,
                timeout=1800
            )
            if result.returncode != 0:
                raise Exception(f"docker save failed: {result.stderr or result.stdout}")

            tar_size_mb = os.path.getsize(local_tar) / (1024 * 1024)
            self._log(log_file, f"Image saved to {local_tar} ({tar_size_mb:.1f} MB)")
        except subprocess.TimeoutExpired:
            raise Exception("docker save timed out after 30 minutes")
        except FileNotFoundError:
            raise Exception("Docker CLI not found on CI server. Install Docker to deploy images.")

        try:
            self._log(log_file, f"Uploading image to remote server: {remote_tar}")
            success, error = ssh.upload_file(local_tar, remote_tar)
            if not success:
                raise Exception(f"Image upload failed: {error}")
            self._log(log_file, f"Image uploaded successfully")

            self._log(log_file, f"Loading Docker image on remote server...")
            success, stdout, stderr = ssh.execute_command(f"docker load -i {remote_tar}")
            if stdout:
                self._log(log_file, f"STDOUT:\n{stdout}")
            if stderr:
                self._log(log_file, f"STDERR:\n{stderr}")
            if not success:
                raise Exception(f"docker load failed on remote server: {stderr}")

            self._log(log_file, f"Docker image loaded on remote server")

            ssh.execute_command(f"rm -f {remote_tar}")
        finally:
            if os.path.exists(local_tar):
                os.remove(local_tar)
                self._log(log_file, f"Cleaned up local image tar")

    def _pull_docker_image(
        self,
        ssh: SSHClient,
        docker_image: str,
        log_file: str
    ) -> None:
        """
        Pull Docker image from registry on remote server.
        """
        self._log(log_file, f"Pulling Docker image on remote server: {docker_image}")
        success, stdout, stderr = ssh.execute_command(f"docker pull {docker_image}")
        if stdout:
            self._log(log_file, f"STDOUT:\n{stdout}")
        if stderr:
            self._log(log_file, f"STDERR:\n{stderr}")
        if not success:
            raise Exception(f"docker pull failed on remote server: {stderr}")
        self._log(log_file, f"Docker image pulled successfully on remote server")

    def _run_docker_container(
        self,
        ssh: SSHClient,
        request: DeployStartRequest,
        deploy: Deploy,
        log_file: str,
        full_image: str
    ) -> None:
        """Stop existing container (if any) and run a new one."""
        container_name = request.container_name

        self._log(log_file, f"Stopping existing container (if any): {container_name}")
        ssh.execute_command(f"docker stop {container_name} 2>/dev/null || true")
        ssh.execute_command(f"docker rm {container_name} 2>/dev/null || true")

        run_cmd = f"docker run -d --name {container_name} --restart unless-stopped"
        if request.port_mapping:
            run_cmd += f" -p {request.port_mapping}"
        run_cmd += f" {full_image}"

        self._log(log_file, f"Running container: {run_cmd}")
        success, stdout, stderr = ssh.execute_command(run_cmd)
        if stdout:
            self._log(log_file, f"STDOUT:\n{stdout}")
        if stderr:
            self._log(log_file, f"STDERR:\n{stderr}")
        if not success:
            raise Exception(f"docker run failed: {stderr}")

        self._log(log_file, f"Container {container_name} started with image {full_image}")

    def _execute_custom_script(self, ssh: SSHClient, deploy_script: str, deploy_path: Optional[str], log_file: str) -> None:
        """
        Execute custom deploy script commands sequentially.
        
        Args:
            ssh: SSH client instance
            deploy_script: Custom deploy script with multiple commands
            deploy_path: Deployment path
            log_file: Log file path
        """
        self._log(log_file, f"Executing custom deploy script...")
        self._log(log_file, f"Deploy script:\n{deploy_script}")
        
        # Split script into commands (one per line)
        commands = [cmd.strip() for cmd in deploy_script.splitlines() if cmd.strip()]
        
        for i, cmd in enumerate(commands, 1):
            self._log(log_file, f"\n=== Executing Command {i}/{len(commands)} ===")
            self._log(log_file, f"Command: {cmd}")
            
            # Execute command with optional deploy path context
            if deploy_path:
                full_cmd = f"cd {deploy_path} && {cmd}"
            else:
                full_cmd = cmd
            success, stdout, stderr = ssh.execute_command(full_cmd)
            
            # Log output
            if stdout:
                self._log(log_file, f"STDOUT:\n{stdout}")
            if stderr:
                self._log(log_file, f"STDERR:\n{stderr}")
            
            # Check if command failed
            if not success:
                raise Exception(f"Command {i} failed: {cmd}\nError: {stderr}")
            
            self._log(log_file, f"Command {i} completed successfully")
        
        self._log(log_file, f"All commands completed successfully")

    def _execute_default_deployment(self, ssh: SSHClient, request: DeployStartRequest, log_file: str) -> None:
        """
        Execute default Python deployment (backward compatibility).
        
        Args:
            ssh: SSH client instance
            request: Deploy start request
            log_file: Log file path
        """
        self._log(log_file, f"Executing default Python deployment...")
        
        # Change to deploy directory
        self._log(log_file, f"Changing to deploy directory: {request.deploy_path}")
        success, stdout, stderr = ssh.execute_command(f"cd {request.deploy_path}")
        if not success:
            raise Exception(f"Failed to change directory: {stderr}")
        self._log(log_file, f"Changed to deploy directory")
        
        # Git pull
        self._log(log_file, f"Pulling latest changes from branch {request.branch}...")
        success, stdout, stderr = ssh.execute_command(f"cd {request.deploy_path} && git pull origin {request.branch}")
        if not success:
            raise Exception(f"Git pull failed: {stderr}")
        self._log(log_file, f"Git pull successful")
        self._log(log_file, stdout)
        
        # Install dependencies
        self._log(log_file, f"Installing dependencies...")
        success, stdout, stderr = ssh.execute_command(f"cd {request.deploy_path} && pip install -r requirements.txt")
        if not success:
            raise Exception(f"pip install failed: {stderr}")
        self._log(log_file, f"Dependencies installed successfully")
        self._log(log_file, stdout)
        
        # Restart service
        self._log(log_file, f"Restarting service: {request.service_name}...")
        success, stdout, stderr = ssh.execute_command(f"systemctl restart {request.service_name}")
        if not success:
            raise Exception(f"Service restart failed: {stderr}")
        self._log(log_file, f"Service restarted successfully")
        
        # Check service status
        self._log(log_file, f"Checking service status...")
        success, stdout, stderr = ssh.execute_command(f"systemctl status {request.service_name}")
        self._log(log_file, f"Service status:")
        self._log(log_file, stdout)
        
        if not success:
            raise Exception(f"Service is not running properly")

    def get_deploy_status(self, deploy_id: int) -> Optional[DeployResponse]:
        """
        Get deploy status by ID.
        
        Args:
            deploy_id: Deploy ID
            
        Returns:
            Deploy response or None if not found
        """
        deploy = self.db.query(Deploy).filter(Deploy.id == deploy_id).first()
        if not deploy:
            return None
        
        return self._deploy_to_response(deploy)

    def get_deploy_log(self, deploy_id: int) -> Optional[str]:
        """
        Get deploy log content.
        
        Args:
            deploy_id: Deploy ID
            
        Returns:
            Log content or None if not found
        """
        deploy = self.db.query(Deploy).filter(Deploy.id == deploy_id).first()
        if not deploy or not deploy.log_path:
            return None
        
        if not os.path.exists(deploy.log_path):
            return "Log file not found"
        
        try:
            with open(deploy.log_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Error reading log file: {str(e)}"

    def get_deploy_history(
        self,
        project_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0
    ) -> tuple[list[DeployResponse], int]:
        """
        Get deploy history with optional filtering.
        
        Args:
            project_id: Filter by project ID (optional)
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            Tuple of (deploys list, total count)
        """
        query = self.db.query(Deploy)
        
        if project_id:
            query = query.filter(Deploy.project_id == project_id)
        
        total = query.count()
        deploys = query.order_by(Deploy.id.desc()).offset(offset).limit(limit).all()
        
        return [self._deploy_to_response(deploy) for deploy in deploys], total

    def _log(self, log_file: str, message: str) -> None:
        """Write message to log file."""
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"{message}\n")

    def _upload_artifact(self, ssh: SSHClient, artifact_path: str, artifact_type: str, deploy_path: str, service_name: str, log_file: str) -> None:
        """
        Upload artifact to remote server and deploy it.

        Args:
            ssh: SSH client instance
            artifact_path: Local path to the artifact
            artifact_type: Type of artifact (file or directory)
            deploy_path: Deployment path on remote server
            service_name: Name of the service to restart
            log_file: Log file path
        """
        import os

        # Convert relative artifact_path to absolute path
        if artifact_path and not os.path.isabs(artifact_path):
            artifact_path = os.path.join(self.workspace_dir, artifact_path)
            self._log(log_file, f"Converted artifact path to absolute: {artifact_path}")

        self._log(log_file, f"=== Uploading Artifact ===")
        self._log(log_file, f"Local artifact: {artifact_path}")
        self._log(log_file, f"Artifact type: {artifact_type}")
        self._log(log_file, f"Deploy path: {deploy_path}")

        if artifact_type == "directory":
            # Upload directory
            remote_temp_path = f"/tmp/{os.path.basename(artifact_path)}"
            self._log(log_file, f"Uploading directory to {remote_temp_path}")

            success, error = ssh.upload_directory(artifact_path, remote_temp_path)
            if not success:
                raise Exception(f"Directory upload failed: {error}")
            self._log(log_file, f"Directory uploaded successfully to {remote_temp_path}")

            # Copy directory to deploy path
            self._log(log_file, f"Copying directory to {deploy_path}")
            copy_cmd = f"sudo cp -r {remote_temp_path}/* {deploy_path}/"
            self._log(log_file, f"Executing: {copy_cmd}")
            success, stdout, stderr = ssh.execute_command(copy_cmd)
            if not success:
                raise Exception(f"Failed to copy directory: {stderr}")
            self._log(log_file, f"Directory copied to {deploy_path}")

        else:
            # Upload file
            artifact_filename = os.path.basename(artifact_path)
            remote_temp_path = f"/tmp/{artifact_filename}"
            self._log(log_file, f"Uploading file to {remote_temp_path}")

            success, error = ssh.upload_file(artifact_path, remote_temp_path)
            if not success:
                raise Exception(f"File upload failed: {error}")
            self._log(log_file, f"File uploaded successfully to {remote_temp_path}")

            # Copy file to deploy path
            self._log(log_file, f"Copying file to {deploy_path}")
            copy_cmd = f"sudo cp {remote_temp_path} {deploy_path}/"
            self._log(log_file, f"Executing: {copy_cmd}")
            success, stdout, stderr = ssh.execute_command(copy_cmd)
            if not success:
                raise Exception(f"Failed to copy file: {stderr}")
            self._log(log_file, f"File copied to {deploy_path}")

        # Restart service if specified
        if service_name:
            self._log(log_file, f"Restarting service: {service_name}")
            restart_cmd = f"sudo systemctl restart {service_name}"
            self._log(log_file, f"Executing: {restart_cmd}")
            success, stdout, stderr = ssh.execute_command(restart_cmd)
            if not success:
                raise Exception(f"Failed to restart service: {stderr}")
            self._log(log_file, f"Service {service_name} restarted successfully")

            # Check service status
            status_cmd = f"sudo systemctl status {service_name}"
            self._log(log_file, f"Executing: {status_cmd}")
            success, stdout, stderr = ssh.execute_command(status_cmd)
            self._log(log_file, f"Service status:\n{stdout}")

    def _deploy_to_response(self, deploy: Deploy) -> DeployResponse:
        """
        Convert Deploy model to DeployResponse schema.

        Args:
            deploy: Deploy model instance

        Returns:
            DeployResponse schema
        """
        return DeployResponse(
            id=deploy.id,
            build_id=deploy.build_id,
            project_id=deploy.project_id,
            project_name=deploy.project_name,
            branch=deploy.branch,
            server_ip=deploy.server_ip,
            server_user=deploy.server_user,
            deploy_path=deploy.deploy_path,
            service_name=deploy.service_name,
            deploy_type=deploy.deploy_type,
            deploy_script=deploy.deploy_script,
            docker_mode=deploy.docker_mode,
            container_name=deploy.container_name,
            image_name=deploy.image_name,
            image_tag=deploy.image_tag,
            port_mapping=deploy.port_mapping,
            docker_image=deploy.docker_image,
            docker_compose_file=deploy.docker_compose_file,
            status=deploy.status,
            start_time=deploy.start_time,
            end_time=deploy.end_time,
            duration=deploy.duration,
            log_path=deploy.log_path,
            error_message=deploy.error_message
        )

    def get_deploy_stages(self, deploy_id: int):
        """
        Get all stages for a deploy.

        Args:
            deploy_id: Deploy ID

        Returns:
            List of DeployStageResponse schemas or None if deploy not found
        """
        from backend.deploy.models import DeployStage
        from backend.deploy.schemas import DeployStageResponse

        # Check if deploy exists
        deploy = self.db.query(Deploy).filter(Deploy.id == deploy_id).first()
        if not deploy:
            return None

        # Get all stages for this deploy
        stages = self.db.query(DeployStage).filter(DeployStage.deploy_id == deploy_id).order_by(DeployStage.id).all()

        return [DeployStageResponse(
            id=stage.id,
            deploy_id=stage.deploy_id,
            stage_name=stage.stage_name,
            status=stage.status,
            started_at=stage.started_at,
            finished_at=stage.finished_at,
            duration=stage.duration,
            log_file=stage.log_file,
            error_message=stage.error_message
        ) for stage in stages]

    def get_stage_log(self, deploy_id: int, stage_name: str):
        """
        Get log content for a specific stage.

        Args:
            deploy_id: Deploy ID
            stage_name: Stage name

        Returns:
            Log content as string or None if not found
        """
        from backend.deploy.models import DeployStage

        # Find the stage
        stage = self.db.query(DeployStage).filter(
            DeployStage.deploy_id == deploy_id,
            DeployStage.stage_name == stage_name
        ).first()

        if not stage or not stage.log_file:
            return None

        # Read the log file
        try:
            with open(stage.log_file, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return None
