"""
Python deployment strategies.
"""
from typing import Optional
from .base import DeploymentContext, DeploymentStrategy


class DjangoStrategy(DeploymentStrategy):
    """Deployment strategy for Django applications"""
    
    @property
    def name(self) -> str:
        return "Django"
    
    @property
    def supported_frameworks(self) -> list[str]:
        return ["Django"]
    
    @property
    def supported_runtimes(self) -> list[str]:
        return ["Python"]
    
    def can_handle(self, framework: str, runtime: str) -> bool:
        return framework == "Django" and runtime == "Python"
    
    def execute(self, context: DeploymentContext, log_func) -> bool:
        try:
            ssh = context.ssh_client
            deploy_path = context.deploy_path
            service_name = context.service_name
            artifact_path = context.artifact_path
            
            log_func(f"Deploying Django application")
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
            success, stdout, stderr = ssh.execute_command(f"cd {deploy_path} && pip install -r requirements.txt")
            if not success:
                log_func(f"✗ Failed to install dependencies")
                log_func(f"  stderr: {stderr}")
                return False
            log_func(f"✓ Success")
            
            # Run database migrations
            log_func("Running database migrations...")
            success, stdout, stderr = ssh.execute_command(f"cd {deploy_path} && python manage.py migrate")
            if not success:
                log_func(f"✗ Failed to run database migrations")
                log_func(f"  stderr: {stderr}")
                return False
            log_func(f"✓ Success")
            
            # Collect static files
            log_func("Collecting static files...")
            success, stdout, stderr = ssh.execute_command(f"cd {deploy_path} && python manage.py collectstatic --noinput")
            if not success:
                log_func(f"✗ Failed to collect static files")
                log_func(f"  stderr: {stderr}")
                return False
            log_func(f"✓ Success")
            
            # Start/restart service
            log_func(f"Starting service {service_name}...")
            success, stdout, stderr = ssh.execute_command(f"cd {deploy_path} && pm2 start gunicorn --name {service_name} -- wsgi:application || pm2 restart {service_name}")
            if not success:
                log_func(f"✗ Failed to start service")
                log_func(f"  stderr: {stderr}")
                return False
            log_func(f"✓ Success")
            
            return True
            
        except Exception as e:
            log_func(f"Error during Django deployment: {str(e)}")
            return False
    
    def get_default_deploy_path(self, project_name: str) -> str:
        return f"/var/www/{project_name.lower()}"
    
    def get_default_service_name(self, project_name: str) -> str:
        return f"{project_name.lower()}"
    
    def validate(self, context: DeploymentContext, log_func) -> bool:
        """Validate Django deployment by checking PM2 process status"""
        log_func(f"Validating Django deployment...")
        
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


class FastAPIStrategy(DeploymentStrategy):
    """Deployment strategy for FastAPI applications"""
    
    @property
    def name(self) -> str:
        return "FastAPI"
    
    @property
    def supported_frameworks(self) -> list[str]:
        return ["FastAPI"]
    
    @property
    def supported_runtimes(self) -> list[str]:
        return ["Python"]

    def can_handle(self, framework: str, runtime: str) -> bool:
        return framework == "FastAPI" and runtime == "Python"
    
    def execute(self, context: DeploymentContext, log_func) -> bool:
        try:
            ssh = context.ssh_client
            deploy_path = context.deploy_path
            service_name = context.service_name
            artifact_path = context.artifact_path
            
            log_func(f"Deploying FastAPI application")
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
            success, stdout, stderr = ssh.execute_command(f"cd {deploy_path} && pip install -r requirements.txt")
            if not success:
                log_func(f"✗ Failed to install dependencies")
                log_func(f"  stderr: {stderr}")
                return False
            log_func(f"✓ Success")
            
            # Start/restart service
            log_func(f"Starting service {service_name}...")
            success, stdout, stderr = ssh.execute_command(f"cd {deploy_path} && pm2 start uvicorn main:app --name {service_name} || pm2 restart {service_name}")
            if not success:
                log_func(f"✗ Failed to start service")
                log_func(f"  stderr: {stderr}")
                return False
            log_func(f"✓ Success")
            
            return True
            
        except Exception as e:
            log_func(f"Error during FastAPI deployment: {str(e)}")
            return False
    
    def get_default_deploy_path(self, project_name: str) -> str:
        return f"/var/www/{project_name.lower()}"
    
    def get_default_service_name(self, project_name: str) -> str:
        return f"{project_name.lower()}"
    
    def validate(self, context: DeploymentContext, log_func) -> bool:
        """Validate FastAPI deployment by checking PM2 process status"""
        log_func(f"Validating FastAPI deployment...")
        
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


class FlaskStrategy(DeploymentStrategy):
    """Deployment strategy for Flask applications"""
    
    @property
    def name(self) -> str:
        return "Flask"
    
    @property
    def supported_frameworks(self) -> list[str]:
        return ["Flask"]
    
    @property
    def supported_runtimes(self) -> list[str]:
        return ["Python"]
    
    def can_handle(self, framework: str, runtime: str) -> bool:
        return framework == "Flask" and runtime == "Python"
    
    def execute(self, context: DeploymentContext, log_func) -> bool:
        try:
            ssh = context.ssh_client
            deploy_path = context.deploy_path
            service_name = context.service_name
            artifact_path = context.artifact_path
            
            log_func(f"Deploying Flask application")
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
            success, stdout, stderr = ssh.execute_command(f"cd {deploy_path} && pip install -r requirements.txt")
            if not success:
                log_func(f"✗ Failed to install dependencies")
                log_func(f"  stderr: {stderr}")
                return False
            log_func(f"✓ Success")
            
            # Start/restart service
            log_func(f"Starting service {service_name}...")
            success, stdout, stderr = ssh.execute_command(f"cd {deploy_path} && pm2 start gunicorn --name {service_name} -- app:app || pm2 restart {service_name}")
            if not success:
                log_func(f"✗ Failed to start service")
                log_func(f"  stderr: {stderr}")
                return False
            log_func(f"✓ Success")
            
            return True
            
        except Exception as e:
            log_func(f"Error during Flask deployment: {str(e)}")
            return False
    
    def get_default_deploy_path(self, project_name: str) -> str:
        return f"/var/www/{project_name.lower()}"
    
    def get_default_service_name(self, project_name: str) -> str:
        return f"{project_name.lower()}"
    
    def validate(self, context: DeploymentContext, log_func) -> bool:
        """Validate Flask deployment by checking PM2 process status"""
        log_func(f"Validating Flask deployment...")
        
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


class SanicStrategy(DeploymentStrategy):
    """Deployment strategy for Sanic applications"""
    
    @property
    def name(self) -> str:
        return "Sanic"
    
    @property
    def supported_frameworks(self) -> list[str]:
        return ["Sanic"]
    
    @property
    def supported_runtimes(self) -> list[str]:
        return ["Python"]
    
    def can_handle(self, framework: str, runtime: str) -> bool:
        return framework == "Sanic" and runtime == "Python"
    
    def execute(self, context: DeploymentContext, log_func) -> bool:
        try:
            ssh = context.ssh_client
            deploy_path = context.deploy_path
            service_name = context.service_name
            artifact_path = context.artifact_path
            
            log_func(f"Deploying Sanic application")
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
            success, stdout, stderr = ssh.execute_command(f"cd {deploy_path} && pip install -r requirements.txt")
            if not success:
                log_func(f"✗ Failed to install dependencies")
                log_func(f"  stderr: {stderr}")
                return False
            log_func(f"✓ Success")
            
            # Start/restart service
            log_func(f"Starting service {service_name}...")
            success, stdout, stderr = ssh.execute_command(f"cd {deploy_path} && pm2 start python --name {service_name} -- server.py || pm2 restart {service_name}")
            if not success:
                log_func(f"✗ Failed to start service")
                log_func(f"  stderr: {stderr}")
                return False
            log_func(f"✓ Success")
            
            return True
            
        except Exception as e:
            log_func(f"Error during Sanic deployment: {str(e)}")
            return False
    
    def get_default_deploy_path(self, project_name: str) -> str:
        return f"/var/www/{project_name.lower()}"
    
    def get_default_service_name(self, project_name: str) -> str:
        return f"{project_name.lower()}"
    
    def validate(self, context: DeploymentContext, log_func) -> bool:
        """Validate Sanic deployment by checking PM2 process status"""
        log_func(f"Validating Sanic deployment...")
        
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
