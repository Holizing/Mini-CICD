"""
Java deployment strategies.
"""
from typing import Optional
from .base import DeploymentContext, DeploymentStrategy


class SpringBootJarStrategy(DeploymentStrategy):
    """Deployment strategy for Spring Boot JAR applications"""
    
    @property
    def name(self) -> str:
        return "Spring Boot JAR"
    
    @property
    def supported_frameworks(self) -> list[str]:
        return ["Spring Boot"]
    
    @property
    def supported_runtimes(self) -> list[str]:
        return ["Java"]

    def can_handle(self, framework: str, runtime: str) -> bool:
        return framework == "Spring Boot" and runtime == "Java"
    
    def execute(self, context: DeploymentContext, log_func) -> bool:
        try:
            ssh = context.ssh_client
            artifact_path = context.artifact_path
            service_name = context.service_name
            deploy_path = context.deploy_path
            
            if not artifact_path:
                log_func("Error: No artifact path provided for JAR deployment")
                return False
            
            # Get artifact name from local path (works on both Windows and Linux)
            import os
            artifact_name = os.path.basename(artifact_path)
            
            log_func(f"Deploying Spring Boot JAR: {artifact_name}")
            log_func(f"Local artifact path: {artifact_path}")
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
            
            # Remove old JAR
            log_func("Removing old JAR...")
            success, stdout, stderr = ssh.execute_command(f"rm -f {deploy_path}/*.jar")
            if not success:
                log_func(f"✗ Failed to remove old JAR")
                log_func(f"  stderr: {stderr}")
                return False
            log_func(f"✓ Success")
            
            # Upload new JAR
            log_func("Uploading new JAR...")
            success, error = ssh.upload_file(artifact_path, f"{deploy_path}/{artifact_name}")
            if not success:
                log_func(f"✗ Failed to upload JAR")
                log_func(f"  error: {error}")
                return False
            log_func(f"✓ Success")
            
            # Set permissions
            log_func("Setting permissions...")
            success, stdout, stderr = ssh.execute_command(f"chmod +x {deploy_path}/{artifact_name}")
            if not success:
                log_func(f"✗ Failed to set permissions")
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
            log_func(f"Error during Spring Boot JAR deployment: {str(e)}")
            return False
    
    def get_default_deploy_path(self, project_name: str) -> str:
        return f"/opt/{project_name.lower()}"
    
    def get_default_service_name(self, project_name: str) -> str:
        return f"{project_name.lower()}"
    
    def validate(self, context: DeploymentContext, log_func) -> bool:
        """Validate Spring Boot JAR deployment by checking systemd service status"""
        log_func(f"Validating Spring Boot JAR deployment...")
        
        # Check systemd service status
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


class SpringBootWarStrategy(DeploymentStrategy):
    """Deployment strategy for Spring Boot WAR applications (Tomcat)"""
    
    @property
    def name(self) -> str:
        return "Spring Boot WAR"
    
    @property
    def supported_frameworks(self) -> list[str]:
        return ["Spring Boot", "Spring", "Java Servlet/JSP"]
    
    @property
    def supported_runtimes(self) -> list[str]:
        return ["Java"]

    @property
    def supported_artifact_types(self) -> list[str]:
        return ["war", "directory"]
    
    def can_handle(self, framework: str, runtime: str) -> bool:
        return framework in ["Spring Boot", "Spring", "Java Servlet/JSP"] and runtime == "Java"
    
    def execute(self, context: DeploymentContext, log_func) -> bool:
        try:
            ssh = context.ssh_client
            artifact_path = context.artifact_path
            service_name = context.service_name
            deploy_path = context.deploy_path
            project_name = context.project_name or "ROOT"
            
            if not artifact_path:
                log_func("Error: No artifact path provided for WAR deployment")
                return False
            
            # Handle directory artifacts - search for WAR files in target/
            import os
            if os.path.isdir(artifact_path):
                log_func(f"Artifact path is a directory: {artifact_path}")
                log_func(f"Searching for WAR files in artifact_path/target/...")
                target_dir = os.path.join(artifact_path, 'target')
                if os.path.isdir(target_dir):
                    war_files = []
                    for file in os.listdir(target_dir):
                        if file.endswith('.war'):
                            war_path = os.path.join(target_dir, file)
                            war_files.append(war_path)
                            log_func(f"Found WAR file: {war_path}")
                    
                    if war_files:
                        # Sort by modification time, newest first
                        war_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                        artifact_path = war_files[0]
                        log_func(f"Using newest WAR file: {artifact_path}")
                    else:
                        log_func(f"ERROR: No WAR artifact found in {target_dir}")
                        return False
                else:
                    log_func(f"ERROR: target directory not found: {target_dir}")
                    return False
            
            # Get artifact name from local path (works on both Windows and Linux)
            artifact_name = os.path.basename(artifact_path)
            
            log_func(f"Deploying WAR: {artifact_name}")
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
            
            # Stop Tomcat
            log_func(f"Stopping Tomcat service {service_name}...")
            success, stdout, stderr = ssh.execute_command(f"sudo -n systemctl stop {service_name} || true")
            log_func(f"✓ Success")
            
            # Remove old WAR
            log_func("Removing old WAR...")
            success, stdout, stderr = ssh.execute_command(f"rm -rf {deploy_path}/{project_name}")
            if not success:
                log_func(f"✗ Failed to remove old WAR directory")
                log_func(f"  stderr: {stderr}")
                return False
            success, stdout, stderr = ssh.execute_command(f"rm -f {deploy_path}/{project_name}.war")
            if not success:
                log_func(f"✗ Failed to remove old WAR file")
                log_func(f"  stderr: {stderr}")
                return False
            log_func(f"✓ Success")
            
            # Upload new WAR
            log_func("Uploading new WAR...")
            success, error = ssh.upload_file(artifact_path, f"{deploy_path}/{artifact_name}")
            if not success:
                log_func(f"✗ Failed to upload WAR")
                log_func(f"  error: {error}")
                return False
            log_func(f"✓ Success")
            
            # Set permissions
            log_func("Setting permissions...")
            success, stdout, stderr = ssh.execute_command(f"chmod 644 {deploy_path}/{artifact_name}")
            if not success:
                log_func(f"✗ Failed to set permissions")
                log_func(f"  stderr: {stderr}")
                return False
            log_func(f"✓ Success")
            
            # Start Tomcat
            log_func(f"Starting Tomcat service {service_name}...")
            success, stdout, stderr = ssh.execute_command(f"sudo -n systemctl start {service_name}")
            if not success:
                log_func(f"✗ Failed to start Tomcat service")
                log_func(f"  stderr: {stderr}")
                return False
            log_func(f"✓ Success")
            
            return True
            
        except Exception as e:
            log_func(f"Error during WAR deployment: {str(e)}")
            return False
    
    def get_default_deploy_path(self, project_name: str) -> str:
        return "/var/lib/tomcat9/webapps"
    
    def get_default_service_name(self, project_name: str) -> str:
        return "tomcat9"
    
    def validate(self, context: DeploymentContext, log_func) -> bool:
        """Validate Tomcat WAR deployment by checking Tomcat service and WAR file"""
        log_func(f"Validating Tomcat WAR deployment...")
        
        # Check Tomcat service status
        if context.service_name:
            log_func(f"Validating Tomcat service {context.service_name}...")
            success, stdout, stderr = context.ssh_client.execute_command(f"sudo systemctl is-active {context.service_name}")
            if success and "active" in stdout:
                log_func(f"✓ Tomcat service active (running)")
            else:
                log_func(f"✗ Tomcat service inactive or not found")
                log_func(f"  stdout: {stdout}")
                log_func(f"  stderr: {stderr}")
                return False
        
        # Check if WAR file exists
        if context.artifact_path:
            import os
            artifact_name = os.path.basename(context.artifact_path)
            log_func(f"Validating WAR file existence...")
            success, stdout, stderr = context.ssh_client.execute_command(f"test -f {context.deploy_path}/{artifact_name}")
            if success:
                log_func(f"✓ WAR file exists at {context.deploy_path}/{artifact_name}")
            else:
                log_func(f"✗ WAR file not found")
                log_func(f"  stderr: {stderr}")
                return False
        
        return True


class JakartaEEStrategy(DeploymentStrategy):
    """Deployment strategy for Jakarta EE applications"""
    
    @property
    def name(self) -> str:
        return "Jakarta EE"
    
    @property
    def supported_frameworks(self) -> list[str]:
        return ["Jakarta EE", "Java EE"]
    
    @property
    def supported_runtimes(self) -> list[str]:
        return ["Java"]
    
    def can_handle(self, framework: str, runtime: str) -> bool:
        return framework in ["Jakarta EE", "Java EE"] and runtime == "Java"
    
    def execute(self, context: DeploymentContext, log_func) -> bool:
        try:
            ssh = context.ssh_client
            artifact_path = context.artifact_path
            service_name = context.service_name
            deploy_path = context.deploy_path
            project_name = context.project_name or "app"
            
            if not artifact_path:
                log_func("Error: No artifact path provided for Jakarta EE deployment")
                return False
            
            import os
            artifact_name = os.path.basename(artifact_path)
            
            log_func(f"Deploying Jakarta EE artifact: {artifact_name}")
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
            
            # Stop application server
            log_func(f"Stopping application server {service_name}...")
            success, stdout, stderr = ssh.execute_command(f"sudo -n systemctl stop {service_name} || true")
            log_func(f"✓ Success")
            
            # Remove old artifact
            log_func("Removing old artifact...")
            success, stdout, stderr = ssh.execute_command(f"rm -rf {deploy_path}/{project_name}")
            if not success:
                log_func(f"✗ Failed to remove old artifact")
                log_func(f"  stderr: {stderr}")
                return False
            log_func(f"✓ Success")
            
            # Upload new artifact
            log_func("Uploading new artifact...")
            success, error = ssh.upload_file(artifact_path, f"{deploy_path}/{artifact_name}")
            if not success:
                log_func(f"✗ Failed to upload artifact")
                log_func(f"  error: {error}")
                return False
            log_func(f"✓ Success")
            
            # Start application server
            log_func(f"Starting application server {service_name}...")
            success, stdout, stderr = ssh.execute_command(f"sudo -n systemctl start {service_name}")
            if not success:
                log_func(f"✗ Failed to start application server")
                log_func(f"  stderr: {stderr}")
                return False
            log_func(f"✓ Success")
            
            return True
            
        except Exception as e:
            log_func(f"Error during Jakarta EE deployment: {str(e)}")
            return False
    
    def get_default_deploy_path(self, project_name: str) -> str:
        return f"/opt/wildfly/deployments"
    
    def get_default_service_name(self, project_name: str) -> str:
        return "wildfly"
    
    def validate(self, context: DeploymentContext, log_func) -> bool:
        """Validate Jakarta EE deployment by checking application server service"""
        log_func(f"Validating Jakarta EE deployment...")
        
        if context.service_name:
            log_func(f"Validating application server service {context.service_name}...")
            success, stdout, stderr = context.ssh_client.execute_command(f"sudo systemctl is-active {context.service_name}")
            if success and "active" in stdout:
                log_func(f"✓ Application server service active (running)")
                return True
            else:
                log_func(f"✗ Application server service inactive or not found")
                log_func(f"  stdout: {stdout}")
                log_func(f"  stderr: {stderr}")
                return False
        else:
            log_func(f"✗ No service name specified for validation")
            return False


class QuarkusStrategy(DeploymentStrategy):
    """Deployment strategy for Quarkus applications"""
    
    @property
    def name(self) -> str:
        return "Quarkus"
    
    @property
    def supported_frameworks(self) -> list[str]:
        return ["Quarkus"]
    
    @property
    def supported_runtimes(self) -> list[str]:
        return ["Java"]
    
    def can_handle(self, framework: str, runtime: str) -> bool:
        return framework == "Quarkus" and runtime == "Java"
    
    def execute(self, context: DeploymentContext, log_func) -> bool:
        try:
            ssh = context.ssh_client
            artifact_path = context.artifact_path
            service_name = context.service_name
            deploy_path = context.deploy_path
            
            if not artifact_path:
                log_func("Error: No artifact path provided for Quarkus deployment")
                return False
            
            import os
            artifact_name = os.path.basename(artifact_path)
            
            log_func(f"Deploying Quarkus artifact: {artifact_name}")
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
            
            # Remove old artifact
            log_func("Removing old artifact...")
            success, stdout, stderr = ssh.execute_command(f"rm -f {deploy_path}/*")
            if not success:
                log_func(f"✗ Failed to remove old artifact")
                log_func(f"  stderr: {stderr}")
                return False
            log_func(f"✓ Success")
            
            # Upload new artifact
            log_func("Uploading new artifact...")
            success, error = ssh.upload_file(artifact_path, f"{deploy_path}/{artifact_name}")
            if not success:
                log_func(f"✗ Failed to upload artifact")
                log_func(f"  error: {error}")
                return False
            log_func(f"✓ Success")
            
            # Set permissions
            log_func("Setting permissions...")
            success, stdout, stderr = ssh.execute_command(f"chmod +x {deploy_path}/{artifact_name}")
            if not success:
                log_func(f"✗ Failed to set permissions")
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
            log_func(f"Error during Quarkus deployment: {str(e)}")
            return False
    
    def get_default_deploy_path(self, project_name: str) -> str:
        return f"/opt/{project_name.lower()}"
    
    def get_default_service_name(self, project_name: str) -> str:
        return f"{project_name.lower()}"
    
    def validate(self, context: DeploymentContext, log_func) -> bool:
        """Validate Quarkus deployment by checking systemd service status"""
        log_func(f"Validating Quarkus deployment...")
        
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


class MicronautStrategy(DeploymentStrategy):
    """Deployment strategy for Micronaut applications"""
    
    @property
    def name(self) -> str:
        return "Micronaut"
    
    @property
    def supported_frameworks(self) -> list[str]:
        return ["Micronaut"]
    
    @property
    def supported_runtimes(self) -> list[str]:
        return ["Java"]
    
    def can_handle(self, framework: str, runtime: str) -> bool:
        return framework == "Micronaut" and runtime == "Java"
    
    def execute(self, context: DeploymentContext, log_func) -> bool:
        try:
            ssh = context.ssh_client
            artifact_path = context.artifact_path
            service_name = context.service_name
            deploy_path = context.deploy_path
            
            if not artifact_path:
                log_func("Error: No artifact path provided for Micronaut deployment")
                return False
            
            import os
            artifact_name = os.path.basename(artifact_path)
            
            log_func(f"Deploying Micronaut artifact: {artifact_name}")
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
            
            # Remove old artifact
            log_func("Removing old artifact...")
            success, stdout, stderr = ssh.execute_command(f"rm -f {deploy_path}/*.jar")
            if not success:
                log_func(f"✗ Failed to remove old artifact")
                log_func(f"  stderr: {stderr}")
                return False
            log_func(f"✓ Success")
            
            # Upload new artifact
            log_func("Uploading new artifact...")
            success, error = ssh.upload_file(artifact_path, f"{deploy_path}/{artifact_name}")
            if not success:
                log_func(f"✗ Failed to upload artifact")
                log_func(f"  error: {error}")
                return False
            log_func(f"✓ Success")
            
            # Set permissions
            log_func("Setting permissions...")
            success, stdout, stderr = ssh.execute_command(f"chmod +x {deploy_path}/{artifact_name}")
            if not success:
                log_func(f"✗ Failed to set permissions")
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
            log_func(f"Error during Micronaut deployment: {str(e)}")
            return False
    
    def get_default_deploy_path(self, project_name: str) -> str:
        return f"/opt/{project_name.lower()}"
    
    def get_default_service_name(self, project_name: str) -> str:
        return f"{project_name.lower()}"
    
    def validate(self, context: DeploymentContext, log_func) -> bool:
        """Validate Micronaut deployment by checking systemd service status"""
        log_func(f"Validating Micronaut deployment...")
        
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
