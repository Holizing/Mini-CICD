"""
Node.js deployment strategies.
"""
from typing import Optional
from .base import DeploymentStrategy, DeploymentContext


class ExpressStrategy(DeploymentStrategy):
    """Deployment strategy for Express applications"""
    
    @property
    def name(self) -> str:
        return "Express"
    
    @property
    def supported_frameworks(self) -> list[str]:
        return ["Express"]
    
    @property
    def supported_runtimes(self) -> list[str]:
        return ["Node.js"]
    
    def can_handle(self, framework: str, runtime: str) -> bool:
        return framework == "Express" and runtime == "Node.js"
    
    def execute(self, context: DeploymentContext, log_func) -> bool:
        try:
            ssh = context.ssh_client
            deploy_path = context.deploy_path
            service_name = context.service_name
            artifact_path = context.artifact_path
            
            log_func(f"Deploying Express application")
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
                # Check if artifact is a directory or file
                import os
                if os.path.isdir(artifact_path):
                    # Upload directory (exclude node_modules)
                    # Upload directly to deploy path to avoid temp directory permission issues
                    success, error = ssh.upload_directory(artifact_path, deploy_path)
                else:
                    # Upload single file
                    success, error = ssh.upload_file(artifact_path, deploy_path)
                if not success:
                    log_func(f"✗ Failed to upload artifact")
                    log_func(f"  error: {error}")
                    return False
                log_func(f"✓ Success")
            
            # Install dependencies
            log_func("Installing dependencies...")
            success, stdout, stderr = ssh.execute_command(f"cd {deploy_path} && npm install --production")
            if not success:
                log_func(f"✗ Failed to install dependencies")
                log_func(f"  stderr: {stderr}")
                return False
            log_func(f"✓ Success")
            
            # Start/restart service
            log_func(f"Starting service {service_name}...")
            success, stdout, stderr = ssh.execute_command(f"cd {deploy_path} && pm2 start app.js --name {service_name} || pm2 restart {service_name}")
            if not success:
                log_func(f"✗ Failed to start service")
                log_func(f"  stderr: {stderr}")
                return False
            log_func(f"✓ Success")
            
            return True
            
        except Exception as e:
            log_func(f"Error during Express deployment: {str(e)}")
            return False
    
    def get_default_deploy_path(self, project_name: str) -> str:
        return f"/var/www/{project_name.lower()}"
    
    def get_default_service_name(self, project_name: str) -> str:
        return f"{project_name.lower()}"
    
    def validate(self, context: DeploymentContext, log_func) -> bool:
        """Validate Express deployment by checking PM2 process status"""
        log_func(f"Validating Express deployment...")
        
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


class NestJSStrategy(DeploymentStrategy):
    """Deployment strategy for NestJS applications"""
    
    @property
    def name(self) -> str:
        return "NestJS"
    
    @property
    def supported_frameworks(self) -> list[str]:
        return ["NestJS"]
    
    @property
    def supported_runtimes(self) -> list[str]:
        return ["Node.js"]
    
    def can_handle(self, framework: str, runtime: str) -> bool:
        return framework == "NestJS" and runtime == "Node.js"
    
    def execute(self, context: DeploymentContext, log_func) -> bool:
        try:
            ssh = context.ssh_client
            deploy_path = context.deploy_path
            service_name = context.service_name
            artifact_path = context.artifact_path
            
            log_func(f"Deploying NestJS application")
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
            success, stdout, stderr = ssh.execute_command(f"cd {deploy_path} && npm install --production")
            if not success:
                log_func(f"✗ Failed to install dependencies")
                log_func(f"  stderr: {stderr}")
                return False
            log_func(f"✓ Success")
            
            # Build application
            log_func("Building application...")
            success, stdout, stderr = ssh.execute_command(f"cd {deploy_path} && npm run build")
            if not success:
                log_func(f"✗ Failed to build application")
                log_func(f"  stderr: {stderr}")
                return False
            log_func(f"✓ Success")
            
            # Start/restart service
            log_func(f"Starting service {service_name}...")
            success, stdout, stderr = ssh.execute_command(f"cd {deploy_path} && pm2 start dist/main.js --name {service_name} || pm2 restart {service_name}")
            if not success:
                log_func(f"✗ Failed to start service")
                log_func(f"  stderr: {stderr}")
                return False
            log_func(f"✓ Success")
            
            return True
            
        except Exception as e:
            log_func(f"Error during NestJS deployment: {str(e)}")
            return False
    
    def get_default_deploy_path(self, project_name: str) -> str:
        return f"/var/www/{project_name.lower()}"
    
    def get_default_service_name(self, project_name: str) -> str:
        return f"{project_name.lower()}"
    
    def validate(self, context: DeploymentContext, log_func) -> bool:
        """Validate NestJS deployment by checking PM2 process status"""
        log_func(f"Validating NestJS deployment...")
        
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


class NextJSStrategy(DeploymentStrategy):
    """Deployment strategy for Next.js applications"""
    
    @property
    def name(self) -> str:
        return "Next.js"
    
    @property
    def supported_frameworks(self) -> list[str]:
        return ["Next.js"]
    
    @property
    def supported_runtimes(self) -> list[str]:
        return ["Node.js"]
    
    def can_handle(self, framework: str, runtime: str) -> bool:
        return framework == "Next.js" and runtime == "Node.js"
    
    def execute(self, context: DeploymentContext, log_func) -> bool:
        try:
            ssh = context.ssh_client
            deploy_path = context.deploy_path
            service_name = context.service_name
            artifact_path = context.artifact_path
            
            log_func(f"Deploying Next.js application")
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
            success, stdout, stderr = ssh.execute_command(f"cd {deploy_path} && npm install --production")
            if not success:
                log_func(f"✗ Failed to install dependencies")
                log_func(f"  stderr: {stderr}")
                return False
            log_func(f"✓ Success")
            
            # Build application
            log_func("Building application...")
            success, stdout, stderr = ssh.execute_command(f"cd {deploy_path} && npm run build")
            if not success:
                log_func(f"✗ Failed to build application")
                log_func(f"  stderr: {stderr}")
                return False
            log_func(f"✓ Success")
            
            # Start/restart service
            log_func(f"Starting service {service_name}...")
            success, stdout, stderr = ssh.execute_command(f"cd {deploy_path} && pm2 start npm --name {service_name} -- start || pm2 restart {service_name}")
            if not success:
                log_func(f"✗ Failed to start service")
                log_func(f"  stderr: {stderr}")
                return False
            log_func(f"✓ Success")
            
            return True
            
        except Exception as e:
            log_func(f"Error during Next.js deployment: {str(e)}")
            return False
    
    def get_default_deploy_path(self, project_name: str) -> str:
        return f"/var/www/{project_name.lower()}"
    
    def get_default_service_name(self, project_name: str) -> str:
        return f"{project_name.lower()}"
    
    def validate(self, context: DeploymentContext, log_func) -> bool:
        """Validate Next.js deployment by checking PM2 process status"""
        log_func(f"Validating Next.js deployment...")
        
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


class StaticSiteStrategy(DeploymentStrategy):
    """Deployment strategy for static sites (React, Vue, Angular, etc.)"""
    
    @property
    def name(self) -> str:
        return "Static Site"
    
    @property
    def supported_frameworks(self) -> list[str]:
        return ["React", "Vue", "Angular", "SvelteKit", "Astro", "Remix", "Static"]
    
    @property
    def supported_runtimes(self) -> list[str]:
        return ["Node.js", "Static"]
    
    def can_handle(self, framework: str, runtime: str) -> bool:
        if framework == "Astro" and runtime == "Static":
            return False
        return framework in self.supported_frameworks and runtime in self.supported_runtimes
    
    def execute(self, context: DeploymentContext, log_func) -> bool:
        try:
            ssh = context.ssh_client
            deploy_path = context.deploy_path
            service_name = context.service_name
            artifact_path = context.artifact_path
            framework = context.additional_params.get('framework', 'Static')
            
            log_func(f"Deploying static site: {framework}")
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
            
            # Upload application files
            if artifact_path:
                log_func("Uploading artifact...")
                success, error = ssh.upload_file(artifact_path, deploy_path)
                if not success:
                    log_func(f"✗ Failed to upload artifact")
                    log_func(f"  error: {error}")
                    return False
                log_func(f"✓ Success")
            
            # Build application
            log_func("Building application...")
            if framework == "React":
                success, stdout, stderr = ssh.execute_command(f"cd {deploy_path} && npm run build")
                build_dir = "build"
            elif framework == "Vue":
                success, stdout, stderr = ssh.execute_command(f"cd {deploy_path} && npm run build")
                build_dir = "dist"
            elif framework == "Angular":
                success, stdout, stderr = ssh.execute_command(f"cd {deploy_path} && npm run build")
                build_dir = "dist"
            elif framework == "SvelteKit":
                success, stdout, stderr = ssh.execute_command(f"cd {deploy_path} && npm run build")
                build_dir = "build"
            elif framework == "Astro":
                success, stdout, stderr = ssh.execute_command(f"cd {deploy_path} && npm run build")
                build_dir = "dist"
            elif framework == "Remix":
                success, stdout, stderr = ssh.execute_command(f"cd {deploy_path} && npm run build")
                build_dir = "build"
            else:
                success, stdout, stderr = ssh.execute_command(f"cd {deploy_path} && npm run build")
                build_dir = "dist"
            
            if not success:
                log_func(f"✗ Failed to build application")
                log_func(f"  stderr: {stderr}")
                return False
            log_func(f"✓ Success")
            
            # Deploy to web server directory
            web_root = "/var/www/html"
            log_func(f"Deploying to web root: {web_root}")
            success, stdout, stderr = ssh.execute_command(f"rm -rf {web_root}/*")
            if not success:
                log_func(f"✗ Failed to clear web root")
                log_func(f"  stderr: {stderr}")
                return False
            success, stdout, stderr = ssh.execute_command(f"cp -r {deploy_path}/{build_dir}/* {web_root}/")
            if not success:
                log_func(f"✗ Failed to copy files to web root")
                log_func(f"  stderr: {stderr}")
                return False
            log_func(f"✓ Success")
            
            # Restart nginx
            log_func("Restarting nginx...")
            success, stdout, stderr = ssh.execute_command("sudo -n systemctl restart nginx || sudo -n systemctl reload nginx")
            if not success:
                log_func(f"✗ Failed to restart nginx")
                log_func(f"  stderr: {stderr}")
                return False
            log_func(f"✓ Success")
            
            return True
            
        except Exception as e:
            log_func(f"Error during static site deployment: {str(e)}")
            return False
    
    def get_default_deploy_path(self, project_name: str) -> str:
        return f"/var/www/{project_name.lower()}"
    
    def get_default_service_name(self, project_name: str) -> str:
        return "nginx"
    
    def validate(self, context: DeploymentContext, log_func) -> bool:
        """Validate static site deployment by checking nginx service and web root"""
        log_func(f"Validating static site deployment...")
        
        # Check nginx service status
        log_func(f"Validating nginx service...")
        success, stdout, stderr = context.ssh_client.execute_command(f"sudo -n systemctl is-active nginx")
        if success and "active" in stdout:
            log_func(f"✓ Nginx service active (running)")
        else:
            log_func(f"✗ Nginx service inactive or not found")
            log_func(f"  stdout: {stdout}")
            log_func(f"  stderr: {stderr}")
            return False
        
        # Check web root directory
        log_func(f"Validating web root directory...")
        success, stdout, stderr = context.ssh_client.execute_command(f"test -d /var/www/html")
        if success:
            log_func(f"✓ Web root directory exists")
        else:
            log_func(f"✗ Web root directory not found")
            log_func(f"  stderr: {stderr}")
            return False
        
        return True


class NuxtStrategy(DeploymentStrategy):
    """Deployment strategy for Nuxt.js applications"""
    
    @property
    def name(self) -> str:
        return "Nuxt"
    
    @property
    def supported_frameworks(self) -> list[str]:
        return ["Nuxt"]
    
    @property
    def supported_runtimes(self) -> list[str]:
        return ["Node.js"]
    
    def can_handle(self, framework: str, runtime: str) -> bool:
        return framework == "Nuxt" and runtime == "Node.js"
    
    def execute(self, context: DeploymentContext, log_func) -> bool:
        try:
            ssh = context.ssh_client
            deploy_path = context.deploy_path
            service_name = context.service_name
            artifact_path = context.artifact_path
            
            log_func(f"Deploying Nuxt.js application")
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
            ssh.execute_command(f"cd {deploy_path} && npm install --production")
            
            # Build application
            log_func("Building application...")
            ssh.execute_command(f"cd {deploy_path} && npm run build")
            
            # Start/restart service
            log_func(f"Starting service {service_name}...")
            ssh.execute_command(f"cd {deploy_path} && pm2 start npm --name {service_name} -- start || pm2 restart {service_name}")
            
            return True
            
        except Exception as e:
            log_func(f"Error during Nuxt.js deployment: {str(e)}")
            return False
    
    def get_default_deploy_path(self, project_name: str) -> str:
        return f"/var/www/{project_name.lower()}"
    
    def get_default_service_name(self, project_name: str) -> str:
        return f"{project_name.lower()}"
