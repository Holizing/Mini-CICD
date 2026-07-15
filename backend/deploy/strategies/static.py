"""
Static site deployment strategies.
"""
from typing import Optional
from .base import DeploymentStrategy, DeploymentContext


class HugoStrategy(DeploymentStrategy):
    """Deployment strategy for Hugo static sites"""
    
    @property
    def name(self) -> str:
        return "Hugo"
    
    @property
    def supported_frameworks(self) -> list[str]:
        return ["Hugo"]
    
    @property
    def supported_runtimes(self) -> list[str]:
        return ["Static"]
    
    def can_handle(self, framework: str, runtime: str) -> bool:
        return framework == "Hugo" and runtime == "Static"
    
    def execute(self, context: DeploymentContext, log_func) -> bool:
        try:
            ssh = context.ssh_client
            deploy_path = context.deploy_path
            service_name = context.service_name
            artifact_path = context.artifact_path
            
            log_func(f"Deploying Hugo static site")
            log_func(f"Deploy path: {deploy_path}")
            log_func(f"Service name: {service_name}")
            
            # Create deploy directory
            log_func("Creating deploy directory...")
            ssh.execute_command(f"mkdir -p {deploy_path}")
            
            # Upload source files
            if artifact_path:
                log_func("Uploading source files...")
                ssh.upload_file(artifact_path, deploy_path)
            
            # Build site
            log_func("Building Hugo site...")
            ssh.execute_command(f"cd {deploy_path} && hugo")
            
            # Deploy to web server directory
            web_root = "/var/www/html"
            log_func(f"Deploying to web root: {web_root}")
            ssh.execute_command(f"rm -rf {web_root}/*")
            ssh.execute_command(f"cp -r {deploy_path}/public/* {web_root}/")
            
            # Restart nginx
            log_func("Restarting nginx...")
            ssh.execute_command("sudo systemctl restart nginx || sudo systemctl reload nginx")
            
            return True
            
        except Exception as e:
            log_func(f"Error during Hugo deployment: {str(e)}")
            return False
    
    def get_default_deploy_path(self, project_name: str) -> str:
        return f"/var/www/{project_name.lower()}"
    
    def get_default_service_name(self, project_name: str) -> str:
        return "nginx"
    
    def validate(self, context: DeploymentContext, log_func) -> bool:
        """Validate Hugo deployment by checking nginx service and web root"""
        log_func(f"Validating Hugo deployment...")
        
        # Check nginx service status
        log_func(f"Validating nginx service...")
        success, stdout, stderr = context.ssh_client.execute_command(f"sudo systemctl is-active nginx")
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


class JekyllStrategy(DeploymentStrategy):
    """Deployment strategy for Jekyll static sites"""
    
    @property
    def name(self) -> str:
        return "Jekyll"
    
    @property
    def supported_frameworks(self) -> list[str]:
        return ["Jekyll"]
    
    @property
    def supported_runtimes(self) -> list[str]:
        return ["Static"]
    
    def can_handle(self, framework: str, runtime: str) -> bool:
        return framework == "Jekyll" and runtime == "Static"
    
    def execute(self, context: DeploymentContext, log_func) -> bool:
        try:
            ssh = context.ssh_client
            deploy_path = context.deploy_path
            service_name = context.service_name
            artifact_path = context.artifact_path
            
            log_func(f"Deploying Jekyll static site")
            log_func(f"Deploy path: {deploy_path}")
            log_func(f"Service name: {service_name}")
            
            # Create deploy directory
            log_func("Creating deploy directory...")
            ssh.execute_command(f"mkdir -p {deploy_path}")
            
            # Upload source files
            if artifact_path:
                log_func("Uploading source files...")
                ssh.upload_file(artifact_path, deploy_path)
            
            # Build site
            log_func("Building Jekyll site...")
            ssh.execute_command(f"cd {deploy_path} && jekyll build")
            
            # Deploy to web server directory
            web_root = "/var/www/html"
            log_func(f"Deploying to web root: {web_root}")
            ssh.execute_command(f"rm -rf {web_root}/*")
            ssh.execute_command(f"cp -r {deploy_path}/_site/* {web_root}/")
            
            # Restart nginx
            log_func("Restarting nginx...")
            ssh.execute_command("sudo systemctl restart nginx || sudo systemctl reload nginx")
            
            return True
            
        except Exception as e:
            log_func(f"Error during Jekyll deployment: {str(e)}")
            return False
    
    def get_default_deploy_path(self, project_name: str) -> str:
        return f"/var/www/{project_name.lower()}"
    
    def get_default_service_name(self, project_name: str) -> str:
        return "nginx"
    
    def validate(self, context: DeploymentContext, log_func) -> bool:
        """Validate Jekyll deployment by checking nginx service and web root"""
        log_func(f"Validating Jekyll deployment...")
        
        # Check nginx service status
        log_func(f"Validating nginx service...")
        success, stdout, stderr = context.ssh_client.execute_command(f"sudo systemctl is-active nginx")
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


class GatsbyStrategy(DeploymentStrategy):
    """Deployment strategy for Gatsby static sites"""
    
    @property
    def name(self) -> str:
        return "Gatsby"
    
    @property
    def supported_frameworks(self) -> list[str]:
        return ["Gatsby"]
    
    @property
    def supported_runtimes(self) -> list[str]:
        return ["Static"]
    
    def can_handle(self, framework: str, runtime: str) -> bool:
        return framework == "Gatsby" and runtime == "Static"
    
    def execute(self, context: DeploymentContext, log_func) -> bool:
        try:
            ssh = context.ssh_client
            deploy_path = context.deploy_path
            service_name = context.service_name
            artifact_path = context.artifact_path
            
            log_func(f"Deploying Gatsby static site")
            log_func(f"Deploy path: {deploy_path}")
            log_func(f"Service name: {service_name}")
            
            # Create deploy directory
            log_func("Creating deploy directory...")
            ssh.execute_command(f"mkdir -p {deploy_path}")
            
            # Upload source files
            if artifact_path:
                log_func("Uploading source files...")
                ssh.upload_file(artifact_path, deploy_path)
            
            # Install dependencies
            log_func("Installing dependencies...")
            ssh.execute_command(f"cd {deploy_path} && npm install --production")
            
            # Build site
            log_func("Building Gatsby site...")
            ssh.execute_command(f"cd {deploy_path} && npm run build")
            
            # Deploy to web server directory
            web_root = "/var/www/html"
            log_func(f"Deploying to web root: {web_root}")
            ssh.execute_command(f"rm -rf {web_root}/*")
            ssh.execute_command(f"cp -r {deploy_path}/public/* {web_root}/")
            
            # Restart nginx
            log_func("Restarting nginx...")
            ssh.execute_command("sudo systemctl restart nginx || sudo systemctl reload nginx")
            
            return True
            
        except Exception as e:
            log_func(f"Error during Gatsby deployment: {str(e)}")
            return False
    
    def get_default_deploy_path(self, project_name: str) -> str:
        return f"/var/www/{project_name.lower()}"
    
    def get_default_service_name(self, project_name: str) -> str:
        return "nginx"
    
    def validate(self, context: DeploymentContext, log_func) -> bool:
        """Validate Gatsby deployment by checking nginx service and web root"""
        log_func(f"Validating Gatsby deployment...")
        
        # Check nginx service status
        log_func(f"Validating nginx service...")
        success, stdout, stderr = context.ssh_client.execute_command(f"sudo systemctl is-active nginx")
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


class AstroStrategy(DeploymentStrategy):
    """Deployment strategy for Astro static sites"""
    
    @property
    def name(self) -> str:
        return "Astro"
    
    @property
    def supported_frameworks(self) -> list[str]:
        return ["Astro"]
    
    @property
    def supported_runtimes(self) -> list[str]:
        return ["Static"]
    
    def can_handle(self, framework: str, runtime: str) -> bool:
        return framework == "Astro" and runtime == "Static"
    
    def execute(self, context: DeploymentContext, log_func) -> bool:
        try:
            ssh = context.ssh_client
            deploy_path = context.deploy_path
            service_name = context.service_name
            artifact_path = context.artifact_path
            
            log_func(f"Deploying Astro static site")
            log_func(f"Deploy path: {deploy_path}")
            log_func(f"Service name: {service_name}")
            
            # Create deploy directory
            log_func("Creating deploy directory...")
            ssh.execute_command(f"mkdir -p {deploy_path}")
            
            # Upload source files
            if artifact_path:
                log_func("Uploading source files...")
                ssh.upload_file(artifact_path, deploy_path)
            
            # Install dependencies
            log_func("Installing dependencies...")
            ssh.execute_command(f"cd {deploy_path} && npm install --production")
            
            # Build site
            log_func("Building Astro site...")
            ssh.execute_command(f"cd {deploy_path} && npm run build")
            
            # Deploy to web server directory
            web_root = "/var/www/html"
            log_func(f"Deploying to web root: {web_root}")
            ssh.execute_command(f"rm -rf {web_root}/*")
            ssh.execute_command(f"cp -r {deploy_path}/dist/* {web_root}/")
            
            # Restart nginx
            log_func("Restarting nginx...")
            ssh.execute_command("sudo systemctl restart nginx || sudo systemctl reload nginx")
            
            return True
            
        except Exception as e:
            log_func(f"Error during Astro deployment: {str(e)}")
            return False
    
    def get_default_deploy_path(self, project_name: str) -> str:
        return f"/var/www/{project_name.lower()}"
    
    def get_default_service_name(self, project_name: str) -> str:
        return "nginx"
    
    def validate(self, context: DeploymentContext, log_func) -> bool:
        """Validate Astro deployment by checking nginx service and web root"""
        log_func(f"Validating Astro deployment...")
        
        # Check nginx service status
        log_func(f"Validating nginx service...")
        success, stdout, stderr = context.ssh_client.execute_command(f"sudo systemctl is-active nginx")
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


class DocusaurusStrategy(DeploymentStrategy):
    """Deployment strategy for Docusaurus static sites"""
    
    @property
    def name(self) -> str:
        return "Docusaurus"
    
    @property
    def supported_frameworks(self) -> list[str]:
        return ["Docusaurus"]
    
    @property
    def supported_runtimes(self) -> list[str]:
        return ["Static"]
    
    def can_handle(self, framework: str, runtime: str) -> bool:
        return framework == "Docusaurus" and runtime == "Static"
    
    def execute(self, context: DeploymentContext, log_func) -> bool:
        try:
            ssh = context.ssh_client
            deploy_path = context.deploy_path
            service_name = context.service_name
            artifact_path = context.artifact_path
            
            log_func(f"Deploying Docusaurus static site")
            log_func(f"Deploy path: {deploy_path}")
            log_func(f"Service name: {service_name}")
            
            # Create deploy directory
            log_func("Creating deploy directory...")
            ssh.execute_command(f"mkdir -p {deploy_path}")
            
            # Upload source files
            if artifact_path:
                log_func("Uploading source files...")
                ssh.upload_file(artifact_path, deploy_path)
            
            # Install dependencies
            log_func("Installing dependencies...")
            ssh.execute_command(f"cd {deploy_path} && npm install --production")
            
            # Build site
            log_func("Building Docusaurus site...")
            ssh.execute_command(f"cd {deploy_path} && npm run build")
            
            # Deploy to web server directory
            web_root = "/var/www/html"
            log_func(f"Deploying to web root: {web_root}")
            ssh.execute_command(f"rm -rf {web_root}/*")
            ssh.execute_command(f"cp -r {deploy_path}/build/* {web_root}/")
            
            # Restart nginx
            log_func("Restarting nginx...")
            ssh.execute_command("sudo systemctl restart nginx || sudo systemctl reload nginx")
            
            return True
            
        except Exception as e:
            log_func(f"Error during Docusaurus deployment: {str(e)}")
            return False
    
    def get_default_deploy_path(self, project_name: str) -> str:
        return f"/var/www/{project_name.lower()}"
    
    def get_default_service_name(self, project_name: str) -> str:
        return "nginx"
    
    def validate(self, context: DeploymentContext, log_func) -> bool:
        """Validate Docusaurus deployment by checking nginx service and web root"""
        log_func(f"Validating Docusaurus deployment...")
        
        # Check nginx service status
        log_func(f"Validating nginx service...")
        success, stdout, stderr = context.ssh_client.execute_command(f"sudo systemctl is-active nginx")
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


class MkDocsStrategy(DeploymentStrategy):
    """Deployment strategy for MkDocs static sites"""
    
    @property
    def name(self) -> str:
        return "MkDocs"
    
    @property
    def supported_frameworks(self) -> list[str]:
        return ["MkDocs"]
    
    @property
    def supported_runtimes(self) -> list[str]:
        return ["Static"]
    
    def can_handle(self, framework: str, runtime: str) -> bool:
        return framework == "MkDocs" and runtime == "Static"
    
    def execute(self, context: DeploymentContext, log_func) -> bool:
        try:
            ssh = context.ssh_client
            deploy_path = context.deploy_path
            service_name = context.service_name
            artifact_path = context.artifact_path
            
            log_func(f"Deploying MkDocs static site")
            log_func(f"Deploy path: {deploy_path}")
            log_func(f"Service name: {service_name}")
            
            # Create deploy directory
            log_func("Creating deploy directory...")
            ssh.execute_command(f"mkdir -p {deploy_path}")
            
            # Upload source files
            if artifact_path:
                log_func("Uploading source files...")
                ssh.upload_file(artifact_path, deploy_path)
            
            # Install dependencies
            log_func("Installing dependencies...")
            ssh.execute_command(f"cd {deploy_path} && pip install -r requirements.txt")
            
            # Build site
            log_func("Building MkDocs site...")
            ssh.execute_command(f"cd {deploy_path} && mkdocs build")
            
            # Deploy to web server directory
            web_root = "/var/www/html"
            log_func(f"Deploying to web root: {web_root}")
            ssh.execute_command(f"rm -rf {web_root}/*")
            ssh.execute_command(f"cp -r {deploy_path}/site/* {web_root}/")
            
            # Restart nginx
            log_func("Restarting nginx...")
            ssh.execute_command("sudo systemctl restart nginx || sudo systemctl reload nginx")
            
            return True
            
        except Exception as e:
            log_func(f"Error during MkDocs deployment: {str(e)}")
            return False
    
    def get_default_deploy_path(self, project_name: str) -> str:
        return f"/var/www/{project_name.lower()}"
    
    def get_default_service_name(self, project_name: str) -> str:
        return "nginx"
    
    def validate(self, context: DeploymentContext, log_func) -> bool:
        """Validate MkDocs deployment by checking nginx service and web root"""
        log_func(f"Validating MkDocs deployment...")
        
        # Check nginx service status
        log_func(f"Validating nginx service...")
        success, stdout, stderr = context.ssh_client.execute_command(f"sudo systemctl is-active nginx")
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
