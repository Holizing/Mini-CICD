"""
Elixir deployment strategies.
"""
from typing import Optional
from .base import DeploymentStrategy, DeploymentContext


class PhoenixStrategy(DeploymentStrategy):
    """Deployment strategy for Phoenix applications"""
    
    @property
    def name(self) -> str:
        return "Phoenix"
    
    @property
    def supported_frameworks(self) -> list[str]:
        return ["Phoenix"]
    
    @property
    def supported_runtimes(self) -> list[str]:
        return ["Elixir"]
    
    def can_handle(self, framework: str, runtime: str) -> bool:
        return framework == "Phoenix" and runtime == "Elixir"
    
    def execute(self, context: DeploymentContext, log_func) -> bool:
        try:
            ssh = context.ssh_client
            deploy_path = context.deploy_path
            service_name = context.service_name
            artifact_path = context.artifact_path
            
            log_func(f"Deploying Phoenix application")
            log_func(f"Deploy path: {deploy_path}")
            log_func(f"Service name: {service_name}")
            
            # Create deploy directory
            log_func("Creating deploy directory...")
            success, stdout, stderr = ssh.execute_command(f"mkdir -p {deploy_path}")
            if not success:
                log_func(f"✗ Failed to create deploy directory")
                log_func(f"  stderr: {stderr}")
                return False
            log_func(f"✓ Success")
            
            # Stop service
            log_func(f"Stopping service {service_name}...")
            success, stdout, stderr = ssh.execute_command(f"sudo -n systemctl stop {service_name} || true")
            log_func(f"✓ Success")
            
            # Upload release package
            if artifact_path:
                log_func("Uploading release package...")
                success, error = ssh.upload_file(artifact_path, deploy_path)
                if not success:
                    log_func(f"✗ Failed to upload release package")
                    log_func(f"  error: {error}")
                    return False
                log_func(f"✓ Success")
            
            # Extract release
            log_func("Extracting release...")
            import os
            artifact_name = os.path.basename(artifact_path) if artifact_path else "release.tar.gz"
            success, stdout, stderr = ssh.execute_command(f"cd {deploy_path} && tar -xzf {artifact_name}")
            if not success:
                log_func(f"✗ Failed to extract release")
                log_func(f"  stderr: {stderr}")
                return False
            log_func(f"✓ Success")
            
            # Run database migrations
            log_func("Running database migrations...")
            success, stdout, stderr = ssh.execute_command(f"cd {deploy_path} && bin/{service_name} eval '{service_name}.Release.migrate'")
            if not success:
                log_func(f"✗ Failed to run database migrations")
                log_func(f"  stderr: {stderr}")
                return False
            log_func(f"✓ Success")
            
            # Start service
            log_func(f"Starting service {service_name}...")
            success, stdout, stderr = ssh.execute_command(f"sudo -n systemctl start {service_name}")
            if not success:
                log_func(f"✗ Failed to start service")
                log_func(f"  stderr: {stderr}")
                return False
            log_func(f"✓ Success")
            
            return True
            
        except Exception as e:
            log_func(f"Error during Phoenix deployment: {str(e)}")
            return False
    
    def get_default_deploy_path(self, project_name: str) -> str:
        return f"/opt/{project_name.lower()}"
    
    def get_default_service_name(self, project_name: str) -> str:
        return f"{project_name.lower()}"
    
    def validate(self, context: DeploymentContext, log_func) -> bool:
        """Validate Phoenix deployment by checking systemd service status"""
        log_func(f"Validating Phoenix deployment...")
        
        if context.service_name:
            log_func(f"Validating service {context.service_name}...")
            success, stdout, stderr = context.ssh_client.execute_command(f"sudo -n systemctl is-active {context.service_name}")
            if success and "active" in stdout:
                log_func(f"✓ Service active (running)")
                return True
            else:
                log_func(f"✗ Service inactive or not found")
                log_func(f"  stdout: {stdout}")
                log_func(f"  stderr: {stderr}")
                return False
        else:
            log_func(f"✗ No service name specified for validation")
            return False
