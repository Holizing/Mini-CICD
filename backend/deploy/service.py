import os
import time
import threading
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from backend.deploy.models import Deploy
from backend.deploy.schemas import DeployStartRequest, DeployResponse
from backend.deploy.ssh import SSHClient
from backend.deploy.utils import get_log_path


class DeployService:
    def __init__(self, db: Session, logs_dir: str):
        self.db = db
        self.logs_dir = logs_dir

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
            status="running",
            log_path=get_log_path(self.logs_dir, 0)  # Temporary, will update after getting ID
        )
        
        self.db.add(deploy)
        self.db.commit()
        self.db.refresh(deploy)

        # Update log path with actual deploy ID
        deploy.log_path = get_log_path(self.logs_dir, deploy.id)
        self.db.commit()

        # Log start
        self._log(deploy.log_path, f"=== Deploy #{deploy.id} Started ===")
        self._log(deploy.log_path, f"Build ID: {request.build_id}")
        self._log(deploy.log_path, f"Project: {request.project_name}")
        self._log(deploy.log_path, f"Branch: {request.branch}")
        self._log(deploy.log_path, f"Server: {request.server_user}@{request.server_ip}")
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
            self._log(log_file, f"Step 1: Getting build record...")
            # Get build record to get artifact path
            from backend.build.models import Build
            build = self.db.query(Build).filter(Build.id == request.build_id).first()
            if build:
                self._log(log_file, f"Build record found: artifact_path={build.artifact_path}, artifact_type={build.artifact_type}")
            else:
                self._log(log_file, f"Warning: Build record not found")

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
            # Connect to server
            self._log(log_file, f"Step 3: Attempting SSH connection (timeout=60s)...")
            success, error = ssh.connect()
            if not success:
                self._log(log_file, f"Step 3: SSH connection failed: {error}")
                raise Exception(error)
            self._log(log_file, f"Step 3: SSH connection established successfully")

            # Upload artifact if exists
            if build and build.artifact_path:
                self._log(log_file, f"Step 4: Uploading artifact...")
                # Fallback to "file" if artifact_type is None (for backward compatibility)
                artifact_type = build.artifact_type or "file"
                self._upload_artifact(ssh, build.artifact_path, artifact_type, request.deploy_path, request.service_name, log_file, request.server_password)
                self._log(log_file, f"Step 4: Artifact upload completed")
            else:
                self._log(log_file, f"Step 4: No artifact to upload, skipping")

            self._log(log_file, f"Step 5: Executing deploy script...")
            # Execute custom deploy script if provided, otherwise use default Python deployment
            # Skip default deployment if artifact was already uploaded (artifact-based deployment)
            if request.deploy_script:
                self._execute_custom_script(ssh, request.deploy_script, request.deploy_path, log_file)
            elif not (build and build.artifact_path):
                # Only run default deployment if no artifact was uploaded
                self._execute_default_deployment(ssh, request, log_file)
            else:
                self._log(log_file, f"Step 5: Skipping default deployment (artifact already uploaded and deployed)")
            self._log(log_file, f"Step 5: Deploy script execution completed")

            self._log(log_file, f"Step 6: Restarting service...")
            # Service restart is handled in _upload_artifact, but log here for clarity
            if request.service_name:
                self._log(log_file, f"Service {request.service_name} restart handled in artifact upload")
            else:
                self._log(log_file, f"No service name specified, skipping restart")

            self._log(log_file, f"Step 7: Closing SSH connection...")
            # Close SSH connection
            ssh.close()
            self._log(log_file, f"Step 7: SSH connection closed")

            self._log(log_file, f"Step 8: Updating deploy record...")
            # Update deploy record as success
            end_time = datetime.utcnow()
            duration = int(time.time() - start_time)

            deploy.status = "success"
            deploy.end_time = end_time
            deploy.duration = duration

            self.db.commit()
            self._log(log_file, f"Step 8: Deploy record updated successfully")
            self._log(log_file, f"=== Deploy #{deploy.id} Completed Successfully in {duration}s ===")

        except Exception as e:
            # Handle errors
            end_time = datetime.utcnow()
            duration = int(time.time() - start_time)

            deploy.status = "failed"
            deploy.end_time = end_time
            deploy.duration = duration
            deploy.error_message = str(e)

            self.db.commit()
            self._log(log_file, f"=== Deploy #{deploy.id} Failed after {duration}s ===")
            self._log(log_file, f"Error: {str(e)}")

    def _execute_custom_script(self, ssh: SSHClient, deploy_script: str, deploy_path: str, log_file: str) -> None:
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
            
            # Execute command with deploy path context
            full_cmd = f"cd {deploy_path} && {cmd}"
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

    def _upload_artifact(self, ssh: SSHClient, artifact_path: str, artifact_type: str, deploy_path: str, service_name: str, log_file: str, sudo_password: Optional[str] = None) -> None:
        """
        Upload artifact to remote server and deploy it.

        Args:
            ssh: SSH client instance
            artifact_path: Local path to the artifact
            artifact_type: Type of artifact (file or directory)
            deploy_path: Deployment path on remote server
            service_name: Name of the service to restart
            log_file: Log file path
            sudo_password: Password for sudo commands
        """
        import os

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
            copy_cmd = f"sudo -S cp -r {remote_temp_path}/* {deploy_path}/"
            self._log(log_file, f"Executing: {copy_cmd}")
            success, stdout, stderr = ssh.execute_command(copy_cmd, sudo_password=sudo_password)
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
            copy_cmd = f"sudo -S cp {remote_temp_path} {deploy_path}/"
            self._log(log_file, f"Executing: {copy_cmd}")
            success, stdout, stderr = ssh.execute_command(copy_cmd, sudo_password=sudo_password)
            if not success:
                raise Exception(f"Failed to copy file: {stderr}")
            self._log(log_file, f"File copied to {deploy_path}")

        # Restart service if specified
        if service_name:
            self._log(log_file, f"Restarting service: {service_name}")
            restart_cmd = f"sudo -S systemctl restart {service_name}"
            self._log(log_file, f"Executing: {restart_cmd}")
            success, stdout, stderr = ssh.execute_command(restart_cmd, sudo_password=sudo_password)
            if not success:
                raise Exception(f"Failed to restart service: {stderr}")
            self._log(log_file, f"Service {service_name} restarted successfully")

            # Check service status
            status_cmd = f"sudo -S systemctl status {service_name}"
            self._log(log_file, f"Executing: {status_cmd}")
            success, stdout, stderr = ssh.execute_command(status_cmd, sudo_password=sudo_password)
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
            status=deploy.status,
            start_time=deploy.start_time,
            end_time=deploy.end_time,
            duration=deploy.duration,
            log_path=deploy.log_path,
            error_message=deploy.error_message
        )
