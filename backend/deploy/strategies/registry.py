"""
Deployment strategy registry and factory.
"""
from typing import Optional, Dict, Any
from .base import DeploymentStrategy, DeploymentContext
from .java import (
    SpringBootJarStrategy,
    SpringBootWarStrategy,
    JakartaEEStrategy,
    QuarkusStrategy,
    MicronautStrategy
)
from .nodejs import (
    ExpressStrategy,
    NestJSStrategy,
    NextJSStrategy,
    StaticSiteStrategy as NodeStaticSiteStrategy,
    NuxtStrategy
)
from .python import (
    DjangoStrategy,
    FastAPIStrategy,
    FlaskStrategy,
    SanicStrategy
)
from .php import (
    LaravelStrategy,
    SymfonyStrategy,
    CodeIgniterStrategy
)
from .dotnet import (
    ASPNetCoreStrategy,
    BlazorServerStrategy
)
from .go import GoStrategy
from .rust import RustStrategy
from .ruby import (
    RailsStrategy,
    SinatraStrategy
)
from .elixir import PhoenixStrategy
from .static import (
    HugoStrategy,
    JekyllStrategy,
    GatsbyStrategy,
    AstroStrategy,
    DocusaurusStrategy,
    MkDocsStrategy
)


class DeploymentStrategyRegistry:
    """
    Registry for deployment strategies.
    
    Manages all available deployment strategies and provides
    methods to select the appropriate strategy based on framework/runtime.
    """
    
    def __init__(self):
        self._strategies: list[DeploymentStrategy] = []
        self._initialize_strategies()
    
    def _initialize_strategies(self):
        """Initialize all available deployment strategies"""
        # Java strategies
        self._strategies.extend([
            SpringBootJarStrategy(),
            SpringBootWarStrategy(),
            JakartaEEStrategy(),
            QuarkusStrategy(),
            MicronautStrategy()
        ])
        
        # Node.js strategies
        self._strategies.extend([
            ExpressStrategy(),
            NestJSStrategy(),
            NextJSStrategy(),
            NuxtStrategy(),
            NodeStaticSiteStrategy()
        ])
        
        # Python strategies
        self._strategies.extend([
            DjangoStrategy(),
            FastAPIStrategy(),
            FlaskStrategy(),
            SanicStrategy()
        ])
        
        # PHP strategies
        self._strategies.extend([
            LaravelStrategy(),
            SymfonyStrategy(),
            CodeIgniterStrategy()
        ])
        
        # .NET strategies
        self._strategies.extend([
            ASPNetCoreStrategy(),
            BlazorServerStrategy()
        ])
        
        # Go strategies
        self._strategies.extend([
            GoStrategy()
        ])
        
        # Rust strategies
        self._strategies.extend([
            RustStrategy()
        ])
        
        # Ruby strategies
        self._strategies.extend([
            RailsStrategy(),
            SinatraStrategy()
        ])
        
        # Elixir strategies
        self._strategies.extend([
            PhoenixStrategy()
        ])
        
        # Static site strategies
        self._strategies.extend([
            HugoStrategy(),
            JekyllStrategy(),
            GatsbyStrategy(),
            AstroStrategy(),
            DocusaurusStrategy(),
            MkDocsStrategy()
        ])
    
    def get_strategy(self, framework: Optional[str], runtime: Optional[str]) -> Optional[DeploymentStrategy]:
        """
        Get the appropriate deployment strategy for the given framework/runtime.
        
        Args:
            framework: Detected framework name
            runtime: Detected runtime name
            
        Returns:
            DeploymentStrategy if found, None otherwise
        """
        if not framework or not runtime:
            return None
        
        # Try to find a strategy that can handle this framework/runtime
        for strategy in self._strategies:
            if strategy.can_handle(framework, runtime):
                return strategy
        
        return None
    
    def get_default_deploy_path(self, framework: Optional[str], runtime: Optional[str], project_name: str) -> str:
        """
        Get default deployment path for the given framework/runtime.
        
        Args:
            framework: Detected framework name
            runtime: Detected runtime name
            project_name: Name of the project
            
        Returns:
            Default deployment path
        """
        strategy = self.get_strategy(framework, runtime)
        if strategy:
            return strategy.get_default_deploy_path(project_name)
        return f"/var/www/{project_name.lower()}"
    
    def get_default_service_name(self, framework: Optional[str], runtime: Optional[str], project_name: str) -> str:
        """
        Get default service name for the given framework/runtime.
        
        Args:
            framework: Detected framework name
            runtime: Detected runtime name
            project_name: Name of the project
            
        Returns:
            Default service name
        """
        strategy = self.get_strategy(framework, runtime)
        if strategy:
            return strategy.get_default_service_name(project_name)
        return project_name.lower()
    
    def list_strategies(self) -> list[Dict[str, Any]]:
        """
        List all available strategies with their supported frameworks/runtimes.
        
        Returns:
            List of strategy information
        """
        return [
            {
                "name": strategy.name,
                "frameworks": strategy.supported_frameworks,
                "runtimes": strategy.supported_runtimes
            }
            for strategy in self._strategies
        ]


# Global registry instance
_registry = None


def get_registry() -> DeploymentStrategyRegistry:
    """
    Get the global deployment strategy registry instance.
    
    Returns:
        DeploymentStrategyRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = DeploymentStrategyRegistry()
    return _registry


def get_strategy(framework: Optional[str], runtime: Optional[str]) -> Optional[DeploymentStrategy]:
    """
    Get the appropriate deployment strategy for the given framework/runtime.
    
    Args:
        framework: Detected framework name
        runtime: Detected runtime name
        
    Returns:
        DeploymentStrategy if found, None otherwise
    """
    return get_registry().get_strategy(framework, runtime)
