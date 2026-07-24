"""Deployment strategy registry, capability reporting, and resolution."""

from dataclasses import dataclass
import os
import re
from typing import Any, Dict, Optional

from .base import DeploymentStrategy, StrategyTier
from .java import (
    SpringBootWarStrategy,
    JakartaEEStrategy,
    QuarkusStrategy,
    MicronautStrategy
)
from .nodejs import (
    NestJSStrategy,
    NextJSStrategy,
    StaticSiteStrategy as NodeStaticSiteStrategy,
    NuxtStrategy
)
from .python import (
    DjangoStrategy,
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
from .verified import (
    VerifiedExpressStrategy,
    VerifiedFastAPIStrategy,
    VerifiedReactStaticStrategy,
    VerifiedSpringBootJarStrategy,
)


class DeploymentStrategyRegistry:
    """
    Registry for deployment strategies.
    
    Manages all available deployment strategies and provides
    methods to select the appropriate strategy based on framework/runtime.
    """
    
    def __init__(self, enable_experimental: Optional[bool] = None):
        self._strategies: list[DeploymentStrategy] = []
        self.enable_experimental = (
            experimental_strategies_enabled()
            if enable_experimental is None
            else enable_experimental
        )
        self._initialize_strategies()
    
    def _initialize_strategies(self):
        """Initialize all available deployment strategies"""
        # Java strategies
        self._strategies.extend([
            VerifiedSpringBootJarStrategy(),
            SpringBootWarStrategy(),
            JakartaEEStrategy(),
            QuarkusStrategy(),
            MicronautStrategy()
        ])
        
        # Node.js strategies
        self._strategies.extend([
            VerifiedExpressStrategy(),
            NestJSStrategy(),
            NextJSStrategy(),
            NuxtStrategy(),
            VerifiedReactStaticStrategy(),
            NodeStaticSiteStrategy()
        ])
        
        # Python strategies
        self._strategies.extend([
            DjangoStrategy(),
            VerifiedFastAPIStrategy(),
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
    
    def get_strategy(
        self,
        framework: Optional[str],
        runtime: Optional[str],
        artifact_type: Optional[str] = None,
    ) -> Optional[DeploymentStrategy]:
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
        
        for strategy in self._strategies:
            if strategy.matches(framework, runtime, artifact_type):
                return strategy

        return None

    def resolve_strategy(
        self,
        framework: Optional[str],
        runtime: Optional[str],
        artifact_type: Optional[str],
    ) -> "StrategyResolution":
        if not framework or not runtime:
            return StrategyResolution(status="unsupported")

        framework_matches = [
            strategy
            for strategy in self._strategies
            if strategy.can_handle(framework, runtime)
        ]
        if not framework_matches:
            return StrategyResolution(status="unsupported")

        strategy = next(
            (
                candidate
                for candidate in framework_matches
                if candidate.supports_artifact(artifact_type)
            ),
            None,
        )
        if strategy is None:
            return StrategyResolution(
                status="artifact_mismatch",
                expected_artifact_types=sorted(
                    {
                        artifact
                        for candidate in framework_matches
                        for artifact in candidate.supported_artifact_types
                    }
                ),
            )

        tier = strategy.tier_for(framework, runtime, artifact_type)
        if tier == StrategyTier.EXPERIMENTAL and not self.enable_experimental:
            return StrategyResolution(
                status="experimental_disabled",
                strategy=strategy,
                tier=tier,
            )

        return StrategyResolution(
            status=(
                "verified"
                if tier == StrategyTier.VERIFIED
                else "experimental_enabled"
            ),
            strategy=strategy,
            tier=tier,
        )
    
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
        return [
            {
                "name": strategy.name,
                "frameworks": strategy.supported_frameworks,
                "runtimes": strategy.supported_runtimes,
                "artifact_types": strategy.supported_artifact_types,
                "required_tools": strategy.required_tools,
            }
            for strategy in self._strategies
        ]

    def list_capabilities(self) -> list[Dict[str, Any]]:
        capabilities: list[Dict[str, Any]] = [
            {
                "id": "docker",
                "name": "Docker",
                "tier": StrategyTier.VERIFIED.value,
                "status": "verified",
                "enabled": True,
                "frameworks": [],
                "runtimes": ["Docker"],
                "artifact_types": ["docker_image"],
                "required_tools": ["docker"],
                "default_health_check_port": None,
            }
        ]

        for strategy in self._strategies:
            profiles_by_tier: dict[
                StrategyTier,
                list[tuple[str, str]],
            ] = {}
            for framework in strategy.supported_frameworks:
                for runtime in strategy.supported_runtimes:
                    if not strategy.can_handle(framework, runtime):
                        continue
                    tier = strategy.tier_for(framework, runtime, None)
                    profiles_by_tier.setdefault(tier, []).append(
                        (framework, runtime)
                    )

            for tier, profiles in profiles_by_tier.items():
                enabled = (
                    tier == StrategyTier.VERIFIED
                    or self.enable_experimental
                )
                suffix = (
                    ""
                    if len(profiles_by_tier) == 1
                    else f"-{tier.value}"
                )
                capabilities.append(
                    {
                        "id": f"{_capability_id(strategy.name)}{suffix}",
                        "name": strategy.name,
                        "tier": tier.value,
                        "status": (
                            tier.value
                            if tier == StrategyTier.VERIFIED
                            else (
                                "experimental_enabled"
                                if enabled
                                else "experimental_disabled"
                            )
                        ),
                        "enabled": enabled,
                        "frameworks": sorted(
                            {framework for framework, _ in profiles}
                        ),
                        "runtimes": sorted(
                            {runtime for _, runtime in profiles}
                        ),
                        "artifact_types": (
                            strategy.supported_artifact_types
                        ),
                        "required_tools": strategy.required_tools,
                        "default_health_check_port": (
                            strategy.default_health_check_port
                        ),
                    }
                )

        return capabilities


@dataclass(frozen=True)
class StrategyResolution:
    status: str
    strategy: Optional[DeploymentStrategy] = None
    tier: Optional[StrategyTier] = None
    expected_artifact_types: Optional[list[str]] = None


def experimental_strategies_enabled() -> bool:
    return os.getenv(
        "MINI_CICD_ENABLE_EXPERIMENTAL_STRATEGIES",
        "false",
    ).strip().lower() in {"1", "true", "yes", "on"}


def _capability_id(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


# Global registry instance
_registry = None
_registry_experimental_setting = None


def get_registry() -> DeploymentStrategyRegistry:
    """
    Get the global deployment strategy registry instance.
    
    Returns:
        DeploymentStrategyRegistry instance
    """
    global _registry, _registry_experimental_setting
    enabled = experimental_strategies_enabled()
    if _registry is None or _registry_experimental_setting != enabled:
        _registry = DeploymentStrategyRegistry(enable_experimental=enabled)
        _registry_experimental_setting = enabled
    return _registry


def get_strategy(
    framework: Optional[str],
    runtime: Optional[str],
    artifact_type: Optional[str] = None,
) -> Optional[DeploymentStrategy]:
    """
    Get the appropriate deployment strategy for the given framework/runtime.
    
    Args:
        framework: Detected framework name
        runtime: Detected runtime name
        
    Returns:
        DeploymentStrategy if found, None otherwise
    """
    return get_registry().get_strategy(framework, runtime, artifact_type)
