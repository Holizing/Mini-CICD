"""Base deployment strategy contracts."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
import shlex
from typing import Any, Dict, Optional


class StrategyTier(str, Enum):
    VERIFIED = "verified"
    EXPERIMENTAL = "experimental"


@dataclass
class DeploymentContext:
    """Runtime inputs shared by deployment strategies."""

    ssh_client: Any
    deploy_path: str
    service_name: str
    artifact_path: Optional[str] = None
    artifact_type: Optional[str] = None
    project_name: Optional[str] = None
    additional_params: Dict[str, Any] = None
    workspace_dir: Optional[str] = None
    release_id: Optional[str] = None
    health_check_port: Optional[int] = None
    health_check_path: str = "/"
    
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

    @property
    def tier(self) -> StrategyTier:
        """Deployment confidence. Existing recipes are experimental by default."""
        return StrategyTier.EXPERIMENTAL

    @property
    def supported_artifact_types(self) -> list[str]:
        """Artifact types accepted by this strategy."""
        return ["directory", "file", "jar", "war"]

    @property
    def required_tools(self) -> list[str]:
        """Remote tools required by this strategy."""
        return []

    @property
    def default_health_check_port(self) -> Optional[int]:
        return None

    def tier_for(
        self,
        framework: str,
        runtime: str,
        artifact_type: Optional[str],
    ) -> StrategyTier:
        """Allow a shared strategy to verify only selected profiles."""
        return self.tier

    def supports_artifact(self, artifact_type: Optional[str]) -> bool:
        return artifact_type is None or artifact_type in self.supported_artifact_types

    def matches(
        self,
        framework: str,
        runtime: str,
        artifact_type: Optional[str] = None,
    ) -> bool:
        return self.can_handle(framework, runtime) and self.supports_artifact(
            artifact_type
        )

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
            service_name = shlex.quote(context.service_name)
            success, stdout, stderr = context.ssh_client.execute_command(
                f"sudo -n systemctl is-active {service_name}"
            )
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
