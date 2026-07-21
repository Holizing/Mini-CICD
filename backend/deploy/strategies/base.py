"""
Base deployment strategy interface.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class DeploymentContext:
    """Context for deployment execution"""
    ssh_client: Any  # SSHClient instance
    deploy_path: str
    service_name: str
    artifact_path: Optional[str] = None
    artifact_type: Optional[str] = None
    project_name: Optional[str] = None
    additional_params: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.additional_params is None:
            self.additional_params = {}


class DeploymentStrategy(ABC):
    """
    Base class for deployment strategies.
    
    Each framework should implement its own strategy by extending this class.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Strategy name"""
        pass
    
    @property
    @abstractmethod
    def supported_frameworks(self) -> list[str]:
        """List of frameworks this strategy supports"""
        pass
    
    @property
    @abstractmethod
    def supported_runtimes(self) -> list[str]:
        """List of runtimes this strategy supports"""
        pass
    
    @abstractmethod
    def can_handle(self, framework: str, runtime: str) -> bool:
        """
        Check if this strategy can handle the given framework/runtime.
        
        Args:
            framework: Detected framework name
            runtime: Detected runtime name
            
        Returns:
            True if this strategy can handle the deployment
        """
        pass
    
    @abstractmethod
    def execute(self, context: DeploymentContext, log_func) -> bool:
        """
        Execute the deployment strategy.
        
        Args:
            context: Deployment context with SSH client and parameters
            log_func: Function to log deployment progress
            
        Returns:
            True if deployment succeeded, False otherwise
        """
        pass
    
    def validate(self, context: DeploymentContext, log_func) -> bool:
        """
        Validate that the deployment was successful.
        
        This method should check that the deployed application is actually running.
        Default implementation checks systemd service status.
        
        Args:
            context: Deployment context with SSH client and parameters
            log_func: Function to log validation progress
            
        Returns:
            True if validation succeeded, False otherwise
        """
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
    
    def get_default_deploy_path(self, project_name: str) -> str:
        """
        Get default deployment path for this strategy.
        
        Args:
            project_name: Name of the project
            
        Returns:
            Default deployment path
        """
        return f"/var/www/{project_name}"
    
    def get_default_service_name(self, project_name: str) -> str:
        """
        Get default service name for this strategy.
        
        Args:
            project_name: Name of the project
            
        Returns:
            Default service name
        """
        return project_name.lower()
