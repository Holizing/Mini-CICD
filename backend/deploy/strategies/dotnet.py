"""
.NET deployment strategies.
"""
from typing import Optional
from .base import DeploymentStrategy, DeploymentContext


class ASPNetCoreStrategy(DeploymentStrategy):
    """Deployment strategy for ASP.NET Core applications"""
    
    @property
    def name(self) -> str:
        return "ASP.NET Core"
    
    @property
    def supported_frameworks(self) -> list[str]:
        return ["ASP.NET Core"]
    
    @property
    def supported_runtimes(self) -> list[str]:
        return [".NET"]
    
    def can_handle(self, framework: str, runtime: str) -> bool:
        return framework == "ASP.NET Core" and runtime == ".NET"
    
    def execute(self, context: DeploymentContext, log_func) -> bool:
        try:
            ssh = context.ssh_client
            deploy_path = context.deploy_path
            service_name = context.service_name
            artifact_path = context.artifact_path
            
            log_func(f"Deploying ASP.NET Core application")
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
            success, stdout, stderr = ssh.execute_command(f"sudo systemctl stop {service_name} || true")
            log_func(f"✓ Success")
            
            # Upload published files
            if artifact_path:
                log_func("Uploading published files...")
                success, error = ssh.upload_file(artifact_path, deploy_path)
                if not success:
                    log_func(f"✗ Failed to upload published files")
                    log_func(f"  error: {error}")
                    return False
                log_func(f"✓ Success")
            
            # Set permissions
            log_func("Setting permissions...")
            success, stdout, stderr = ssh.execute_command(f"chmod +x {deploy_path}/*.dll")
            if not success:
                log_func(f"✗ Failed to set permissions")
                log_func(f"  stderr: {stderr}")
                return False
            log_func(f"✓ Success")
            
            # Start service
            log_func(f"Starting service {service_name}...")
            success, stdout, stderr = ssh.execute_command(f"sudo systemctl start {service_name}")
            if not success:
                log_func(f"✗ Failed to start service")
                log_func(f"  stderr: {stderr}")
                return False
            log_func(f"✓ Success")
            
            return True
            
        except Exception as e:
            log_func(f"Error during ASP.NET Core deployment: {str(e)}")
            return False
    
    def get_default_deploy_path(self, project_name: str) -> str:
        return f"/var/www/{project_name.lower()}"
    
    def get_default_service_name(self, project_name: str) -> str:
        return f"{project_name.lower()}"
    
    def validate(self, context: DeploymentContext, log_func) -> bool:
        """Validate ASP.NET Core deployment by checking systemd service status"""
        log_func(f"Validating ASP.NET Core deployment...")
        
        if context.service_name:
            log_func(f"Validating service {context.service_name}...")
            success, stdout, stderr = context.ssh_client.execute_command(f"sudo systemctl is-active {context.service_name}")
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


class BlazorServerStrategy(DeploymentStrategy):
    """Deployment strategy for Blazor Server applications"""
    
    @property
    def name(self) -> str:
        return "Blazor Server"
    
    @property
    def supported_frameworks(self) -> list[str]:
        return ["Blazor Server"]
    
    @property
    def supported_runtimes(self) -> list[str]:
        return [".NET"]
    
    def can_handle(self, framework: str, runtime: str) -> bool:
        return framework == "Blazor Server" and runtime == ".NET"
    
    def execute(self, context: DeploymentContext, log_func) -> bool:
        try:
            ssh = context.ssh_client
            deploy_path = context.deploy_path
            service_name = context.service_name
            artifact_path = context.artifact_path
            
            log_func(f"Deploying Blazor Server application")
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
            success, stdout, stderr = ssh.execute_command(f"sudo systemctl stop {service_name} || true")
            log_func(f"✓ Success")
            
            # Upload published files
            if artifact_path:
                log_func("Uploading published files...")
                success, error = ssh.upload_file(artifact_path, deploy_path)
                if not success:
                    log_func(f"✗ Failed to upload published files")
                    log_func(f"  error: {error}")
                    return False
                log_func(f"✓ Success")
            
            # Set permissions
            log_func("Setting permissions...")
            success, stdout, stderr = ssh.execute_command(f"chmod +x {deploy_path}/*.dll")
            if not success:
                log_func(f"✗ Failed to set permissions")
                log_func(f"  stderr: {stderr}")
                return False
            log_func(f"✓ Success")
            
            # Start service
            log_func(f"Starting service {service_name}...")
            success, stdout, stderr = ssh.execute_command(f"sudo systemctl start {service_name}")
            if not success:
                log_func(f"✗ Failed to start service")
                log_func(f"  stderr: {stderr}")
                return False
            log_func(f"✓ Success")
            
            return True
            
        except Exception as e:
            log_func(f"Error during Blazor Server deployment: {str(e)}")
            return False
    
    def get_default_deploy_path(self, project_name: str) -> str:
        return f"/var/www/{project_name.lower()}"
    
    def get_default_service_name(self, project_name: str) -> str:
        return f"{project_name.lower()}"
    
    def validate(self, context: DeploymentContext, log_func) -> bool:
        """Validate Blazor Server deployment by checking systemd service status"""
        log_func(f"Validating Blazor Server deployment...")
        
        if context.service_name:
            log_func(f"Validating service {context.service_name}...")
            success, stdout, stderr = context.ssh_client.execute_command(f"sudo systemctl is-active {context.service_name}")
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
