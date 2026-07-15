"""
Ruby deployment strategies.
"""
from typing import Optional
from .base import DeploymentStrategy, DeploymentContext


class RailsStrategy(DeploymentStrategy):
    """Deployment strategy for Ruby on Rails applications"""
    
    @property
    def name(self) -> str:
        return "Ruby on Rails"
    
    @property
    def supported_frameworks(self) -> list[str]:
        return ["Rails", "Ruby on Rails"]
    
    @property
    def supported_runtimes(self) -> list[str]:
        return ["Ruby"]
    
    def can_handle(self, framework: str, runtime: str) -> bool:
        return framework in ["Rails", "Ruby on Rails"] and runtime == "Ruby"
    
    def execute(self, context: DeploymentContext, log_func) -> bool:
        try:
            ssh = context.ssh_client
            deploy_path = context.deploy_path
            service_name = context.service_name
            artifact_path = context.artifact_path
            
            log_func(f"Deploying Ruby on Rails application")
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
            success, stdout, stderr = ssh.execute_command(f"pm2 stop {service_name} || true")
            log_func(f"✓ Success")
            
            # Upload application files
            if artifact_path:
                log_func("Uploading artifact...")
                success, error = ssh.upload_file(artifact_path, deploy_path)
                if not success:
                    log_func(f"✗ Failed to upload artifact")
                    log_func(f"  error: {error}")
                    return False
                log_func(f"✓ Success")
            
            # Install dependencies
            log_func("Installing dependencies...")
            success, stdout, stderr = ssh.execute_command(f"cd {deploy_path} && bundle install --deployment --without development test")
            if not success:
                log_func(f"✗ Failed to install dependencies")
                log_func(f"  stderr: {stderr}")
                return False
            log_func(f"✓ Success")
            
            # Run database migrations
            log_func("Running database migrations...")
            success, stdout, stderr = ssh.execute_command(f"cd {deploy_path} && bundle exec rails db:migrate RAILS_ENV=production")
            if not success:
                log_func(f"✗ Failed to run database migrations")
                log_func(f"  stderr: {stderr}")
                return False
            log_func(f"✓ Success")
            
            # Precompile assets
            log_func("Precompiling assets...")
            success, stdout, stderr = ssh.execute_command(f"cd {deploy_path} && bundle exec rails assets:precompile RAILS_ENV=production")
            if not success:
                log_func(f"✗ Failed to precompile assets")
                log_func(f"  stderr: {stderr}")
                return False
            log_func(f"✓ Success")
            
            # Start/restart service
            log_func(f"Starting service {service_name}...")
            success, stdout, stderr = ssh.execute_command(f"cd {deploy_path} && pm2 start bundle --name {service_name} -- exec puma -C config/puma.rb || pm2 restart {service_name}")
            if not success:
                log_func(f"✗ Failed to start service")
                log_func(f"  stderr: {stderr}")
                return False
            log_func(f"✓ Success")
            
            return True
            
        except Exception as e:
            log_func(f"Error during Rails deployment: {str(e)}")
            return False
    
    def get_default_deploy_path(self, project_name: str) -> str:
        return f"/var/www/{project_name.lower()}"
    
    def get_default_service_name(self, project_name: str) -> str:
        return f"{project_name.lower()}"
    
    def validate(self, context: DeploymentContext, log_func) -> bool:
        """Validate Rails deployment by checking PM2 process status"""
        log_func(f"Validating Rails deployment...")
        
        if context.service_name:
            log_func(f"Validating PM2 process {context.service_name}...")
            success, stdout, stderr = context.ssh_client.execute_command(f"pm2 status {context.service_name}")
            if success and "online" in stdout:
                log_func(f"✓ PM2 process online (running)")
                return True
            else:
                log_func(f"✗ PM2 process not online")
                log_func(f"  stdout: {stdout}")
                log_func(f"  stderr: {stderr}")
                return False
        else:
            log_func(f"✗ No service name specified for validation")
            return False


class SinatraStrategy(DeploymentStrategy):
    """Deployment strategy for Sinatra applications"""
    
    @property
    def name(self) -> str:
        return "Sinatra"
    
    @property
    def supported_frameworks(self) -> list[str]:
        return ["Sinatra"]
    
    @property
    def supported_runtimes(self) -> list[str]:
        return ["Ruby"]
    
    def can_handle(self, framework: str, runtime: str) -> bool:
        return framework == "Sinatra" and runtime == "Ruby"
    
    def execute(self, context: DeploymentContext, log_func) -> bool:
        try:
            ssh = context.ssh_client
            deploy_path = context.deploy_path
            service_name = context.service_name
            artifact_path = context.artifact_path
            
            log_func(f"Deploying Sinatra application")
            log_func(f"Deploy path: {deploy_path}")
            log_func(f"Service name: {service_name}")
            
            # Create deploy directory
            log_func("Creating deploy directory...")
            ssh.execute_command(f"mkdir -p {deploy_path}")
            
            # Stop service
            log_func(f"Stopping service {service_name}...")
            ssh.execute_command(f"pm2 stop {service_name} || true")
            
            # Upload application files
            if artifact_path:
                log_func("Uploading artifact...")
                ssh.upload_file(artifact_path, deploy_path)
            
            # Install dependencies
            log_func("Installing dependencies...")
            ssh.execute_command(f"cd {deploy_path} && bundle install --deployment --without development test")
            
            # Start/restart service
            log_func(f"Starting service {service_name}...")
            ssh.execute_command(f"cd {deploy_path} && pm2 start bundle --name {service_name} -- exec rackup -p 4567 || pm2 restart {service_name}")
            
            return True
            
        except Exception as e:
            log_func(f"Error during Sinatra deployment: {str(e)}")
            return False
    
    def get_default_deploy_path(self, project_name: str) -> str:
        return f"/var/www/{project_name.lower()}"
    
    def get_default_service_name(self, project_name: str) -> str:
        return f"{project_name.lower()}"
