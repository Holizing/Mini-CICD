"""
PHP deployment strategies.
"""
from typing import Optional
from .base import DeploymentStrategy, DeploymentContext


class LaravelStrategy(DeploymentStrategy):
    """Deployment strategy for Laravel applications"""
    
    @property
    def name(self) -> str:
        return "Laravel"
    
    @property
    def supported_frameworks(self) -> list[str]:
        return ["Laravel"]
    
    @property
    def supported_runtimes(self) -> list[str]:
        return ["PHP"]
    
    def can_handle(self, framework: str, runtime: str) -> bool:
        return framework == "Laravel" and runtime == "PHP"
    
    def execute(self, context: DeploymentContext, log_func) -> bool:
        try:
            ssh = context.ssh_client
            deploy_path = context.deploy_path
            service_name = context.service_name
            artifact_path = context.artifact_path
            
            log_func(f"Deploying Laravel application")
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
            
            # Install dependencies
            log_func("Installing dependencies...")
            success, stdout, stderr = ssh.execute_command(f"cd {deploy_path} && composer install --no-dev --optimize-autoloader")
            if not success:
                log_func(f"✗ Failed to install dependencies")
                log_func(f"  stderr: {stderr}")
                return False
            log_func(f"✓ Success")
            
            # Clear application cache
            log_func("Clearing application cache...")
            success, stdout, stderr = ssh.execute_command(f"cd {deploy_path} && php artisan cache:clear")
            if not success:
                log_func(f"✗ Failed to clear cache")
                log_func(f"  stderr: {stderr}")
                return False
            success, stdout, stderr = ssh.execute_command(f"cd {deploy_path} && php artisan config:clear")
            if not success:
                log_func(f"✗ Failed to clear config cache")
                log_func(f"  stderr: {stderr}")
                return False
            success, stdout, stderr = ssh.execute_command(f"cd {deploy_path} && php artisan route:clear")
            if not success:
                log_func(f"✗ Failed to clear route cache")
                log_func(f"  stderr: {stderr}")
                return False
            success, stdout, stderr = ssh.execute_command(f"cd {deploy_path} && php artisan view:clear")
            if not success:
                log_func(f"✗ Failed to clear view cache")
                log_func(f"  stderr: {stderr}")
                return False
            log_func(f"✓ Success")
            
            # Run optimizations
            log_func("Running optimizations...")
            success, stdout, stderr = ssh.execute_command(f"cd {deploy_path} && php artisan config:cache")
            if not success:
                log_func(f"✗ Failed to cache config")
                log_func(f"  stderr: {stderr}")
                return False
            success, stdout, stderr = ssh.execute_command(f"cd {deploy_path} && php artisan route:cache")
            if not success:
                log_func(f"✗ Failed to cache routes")
                log_func(f"  stderr: {stderr}")
                return False
            success, stdout, stderr = ssh.execute_command(f"cd {deploy_path} && php artisan view:cache")
            if not success:
                log_func(f"✗ Failed to cache views")
                log_func(f"  stderr: {stderr}")
                return False
            log_func(f"✓ Success")
            
            # Set permissions
            log_func("Setting permissions...")
            success, stdout, stderr = ssh.execute_command(f"cd {deploy_path} && chown -R www-data:www-data storage bootstrap/cache")
            if not success:
                log_func(f"✗ Failed to set ownership")
                log_func(f"  stderr: {stderr}")
                return False
            success, stdout, stderr = ssh.execute_command(f"cd {deploy_path} && chmod -R 775 storage bootstrap/cache")
            if not success:
                log_func(f"✗ Failed to set permissions")
                log_func(f"  stderr: {stderr}")
                return False
            log_func(f"✓ Success")
            
            # Restart PHP-FPM
            log_func("Restarting PHP-FPM...")
            success, stdout, stderr = ssh.execute_command("sudo systemctl restart php-fpm || sudo systemctl restart php8.1-fpm || sudo systemctl restart php8.2-fpm")
            if not success:
                log_func(f"✗ Failed to restart PHP-FPM")
                log_func(f"  stderr: {stderr}")
                return False
            log_func(f"✓ Success")
            
            return True
            
        except Exception as e:
            log_func(f"Error during Laravel deployment: {str(e)}")
            return False
    
    def get_default_deploy_path(self, project_name: str) -> str:
        return f"/var/www/{project_name.lower()}"
    
    def get_default_service_name(self, project_name: str) -> str:
        return "php-fpm"
    
    def validate(self, context: DeploymentContext, log_func) -> bool:
        """Validate Laravel deployment by checking PHP-FPM service and web directory"""
        log_func(f"Validating Laravel deployment...")
        
        # Check PHP-FPM service status
        log_func(f"Validating PHP-FPM service...")
        success, stdout, stderr = context.ssh_client.execute_command("sudo systemctl is-active php-fpm || sudo systemctl is-active php8.1-fpm || sudo systemctl is-active php8.2-fpm")
        if success and "active" in stdout:
            log_func(f"✓ PHP-FPM service active (running)")
        else:
            log_func(f"✗ PHP-FPM service inactive or not found")
            log_func(f"  stdout: {stdout}")
            log_func(f"  stderr: {stderr}")
            return False
        
        # Check web directory
        log_func(f"Validating web directory...")
        success, stdout, stderr = context.ssh_client.execute_command(f"test -d {context.deploy_path}/public")
        if success:
            log_func(f"✓ Web directory exists")
        else:
            log_func(f"✗ Web directory not found")
            log_func(f"  stderr: {stderr}")
            return False
        
        return True


class SymfonyStrategy(DeploymentStrategy):
    """Deployment strategy for Symfony applications"""
    
    @property
    def name(self) -> str:
        return "Symfony"
    
    @property
    def supported_frameworks(self) -> list[str]:
        return ["Symfony"]
    
    @property
    def supported_runtimes(self) -> list[str]:
        return ["PHP"]
    
    def can_handle(self, framework: str, runtime: str) -> bool:
        return framework == "Symfony" and runtime == "PHP"
    
    def execute(self, context: DeploymentContext, log_func) -> bool:
        try:
            ssh = context.ssh_client
            deploy_path = context.deploy_path
            service_name = context.service_name
            artifact_path = context.artifact_path
            
            log_func(f"Deploying Symfony application")
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
            
            # Install dependencies
            log_func("Installing dependencies...")
            success, stdout, stderr = ssh.execute_command(f"cd {deploy_path} && composer install --no-dev --optimize-autoloader")
            if not success:
                log_func(f"✗ Failed to install dependencies")
                log_func(f"  stderr: {stderr}")
                return False
            log_func(f"✓ Success")
            
            # Clear cache
            log_func("Clearing cache...")
            success, stdout, stderr = ssh.execute_command(f"cd {deploy_path} && php bin/console cache:clear")
            if not success:
                log_func(f"✗ Failed to clear cache")
                log_func(f"  stderr: {stderr}")
                return False
            success, stdout, stderr = ssh.execute_command(f"cd {deploy_path} && php bin/console cache:warmup --env=prod")
            if not success:
                log_func(f"✗ Failed to warm up cache")
                log_func(f"  stderr: {stderr}")
                return False
            log_func(f"✓ Success")
            
            # Set permissions
            log_func("Setting permissions...")
            success, stdout, stderr = ssh.execute_command(f"cd {deploy_path} && chown -R www-data:www-data var")
            if not success:
                log_func(f"✗ Failed to set ownership")
                log_func(f"  stderr: {stderr}")
                return False
            success, stdout, stderr = ssh.execute_command(f"cd {deploy_path} && chmod -R 775 var")
            if not success:
                log_func(f"✗ Failed to set permissions")
                log_func(f"  stderr: {stderr}")
                return False
            log_func(f"✓ Success")
            
            # Restart PHP-FPM
            log_func("Restarting PHP-FPM...")
            success, stdout, stderr = ssh.execute_command("sudo systemctl restart php-fpm || sudo systemctl restart php8.1-fpm || sudo systemctl restart php8.2-fpm")
            if not success:
                log_func(f"✗ Failed to restart PHP-FPM")
                log_func(f"  stderr: {stderr}")
                return False
            log_func(f"✓ Success")
            
            return True
            
        except Exception as e:
            log_func(f"Error during Symfony deployment: {str(e)}")
            return False
    
    def get_default_deploy_path(self, project_name: str) -> str:
        return f"/var/www/{project_name.lower()}"
    
    def get_default_service_name(self, project_name: str) -> str:
        return "php-fpm"
    
    def validate(self, context: DeploymentContext, log_func) -> bool:
        """Validate Symfony deployment by checking PHP-FPM service and web directory"""
        log_func(f"Validating Symfony deployment...")
        
        # Check PHP-FPM service status
        log_func(f"Validating PHP-FPM service...")
        success, stdout, stderr = context.ssh_client.execute_command("sudo systemctl is-active php-fpm || sudo systemctl is-active php8.1-fpm || sudo systemctl is-active php8.2-fpm")
        if success and "active" in stdout:
            log_func(f"✓ PHP-FPM service active (running)")
        else:
            log_func(f"✗ PHP-FPM service inactive or not found")
            log_func(f"  stdout: {stdout}")
            log_func(f"  stderr: {stderr}")
            return False
        
        # Check web directory
        log_func(f"Validating web directory...")
        success, stdout, stderr = context.ssh_client.execute_command(f"test -d {context.deploy_path}/public")
        if success:
            log_func(f"✓ Web directory exists")
        else:
            log_func(f"✗ Web directory not found")
            log_func(f"  stderr: {stderr}")
            return False
        
        return True


class CodeIgniterStrategy(DeploymentStrategy):
    """Deployment strategy for CodeIgniter applications"""
    
    @property
    def name(self) -> str:
        return "CodeIgniter"
    
    @property
    def supported_frameworks(self) -> list[str]:
        return ["CodeIgniter"]
    
    @property
    def supported_runtimes(self) -> list[str]:
        return ["PHP"]
    
    def can_handle(self, framework: str, runtime: str) -> bool:
        return framework == "CodeIgniter" and runtime == "PHP"
    
    def execute(self, context: DeploymentContext, log_func) -> bool:
        try:
            ssh = context.ssh_client
            deploy_path = context.deploy_path
            service_name = context.service_name
            artifact_path = context.artifact_path
            
            log_func(f"Deploying CodeIgniter application")
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
            
            # Set permissions
            log_func("Setting permissions...")
            success, stdout, stderr = ssh.execute_command(f"cd {deploy_path} && chown -R www-data:www-data writable")
            if not success:
                log_func(f"✗ Failed to set ownership")
                log_func(f"  stderr: {stderr}")
                return False
            success, stdout, stderr = ssh.execute_command(f"cd {deploy_path} && chmod -R 775 writable")
            if not success:
                log_func(f"✗ Failed to set permissions")
                log_func(f"  stderr: {stderr}")
                return False
            log_func(f"✓ Success")
            
            # Restart PHP-FPM
            log_func("Restarting PHP-FPM...")
            success, stdout, stderr = ssh.execute_command("sudo systemctl restart php-fpm || sudo systemctl restart php8.1-fpm || sudo systemctl restart php8.2-fpm")
            if not success:
                log_func(f"✗ Failed to restart PHP-FPM")
                log_func(f"  stderr: {stderr}")
                return False
            log_func(f"✓ Success")
            
            return True
            
        except Exception as e:
            log_func(f"Error during CodeIgniter deployment: {str(e)}")
            return False
    
    def get_default_deploy_path(self, project_name: str) -> str:
        return f"/var/www/{project_name.lower()}"
    
    def get_default_service_name(self, project_name: str) -> str:
        return "php-fpm"
    
    def validate(self, context: DeploymentContext, log_func) -> bool:
        """Validate CodeIgniter deployment by checking PHP-FPM service and web directory"""
        log_func(f"Validating CodeIgniter deployment...")
        
        # Check PHP-FPM service status
        log_func(f"Validating PHP-FPM service...")
        success, stdout, stderr = context.ssh_client.execute_command("sudo systemctl is-active php-fpm || sudo systemctl is-active php8.1-fpm || sudo systemctl is-active php8.2-fpm")
        if success and "active" in stdout:
            log_func(f"✓ PHP-FPM service active (running)")
        else:
            log_func(f"✗ PHP-FPM service inactive or not found")
            log_func(f"  stdout: {stdout}")
            log_func(f"  stderr: {stderr}")
            return False
        
        # Check web directory
        log_func(f"Validating web directory...")
        success, stdout, stderr = context.ssh_client.execute_command(f"test -d {context.deploy_path}/public")
        if success:
            log_func(f"✓ Web directory exists")
        else:
            log_func(f"✗ Web directory not found")
            log_func(f"  stderr: {stderr}")
            return False
        
        return True
