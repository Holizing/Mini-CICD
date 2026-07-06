import os
import time
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
        
        # Execute deploy synchronously (in production, use Celery or similar)
        self._execute_deploy_sync(deploy, request)
        
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
            # Initialize SSH client
            ssh = SSHClient(
                host=request.server_ip,
                username=request.server_user,
                password=request.server_password,
                key=request.server_ssh_key
            )
            
            # Connect to server
            self._log(log_file, f"Connecting to SSH server {request.server_user}@{request.server_ip}...")
            success, error = ssh.connect()
            if not success:
                raise Exception(error)
            self._log(log_file, f"SSH connection established")
            
            # Execute custom deploy script if provided, otherwise use default Python deployment
            if request.deploy_script:
                self._execute_custom_script(ssh, request.deploy_script, request.deploy_path, log_file)
            else:
                self._execute_default_deployment(ssh, request, log_file)
            
            # Close SSH connection
            ssh.close()
            self._log(log_file, f"SSH connection closed")
            
            # Update deploy record as success
            end_time = datetime.utcnow()
            duration = int(time.time() - start_time)
            
            deploy.status = "success"
            deploy.end_time = end_time
            deploy.duration = duration
            
            self.db.commit()
            self._log(log_file, f"=== Deploy #{deploy.id} Completed Successfully ===")
            
        except Exception as e:
            # Handle errors
            end_time = datetime.utcnow()
            duration = int(time.time() - start_time)
            
            deploy.status = "failed"
            deploy.end_time = end_time
            deploy.duration = duration
            deploy.error_message = str(e)
            
            self.db.commit()
            self._log(log_file, f"=== Deploy #{deploy.id} Failed ===")
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
