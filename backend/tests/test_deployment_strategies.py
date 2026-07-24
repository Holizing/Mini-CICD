"""Regression tests for deployment strategy selection and execution."""

import json

import pytest
from backend.build.runner import BuildRunner
from backend.deploy.artifacts import (
    DeploymentSafetyError,
    validate_identifier,
    validate_remote_deploy_path,
    wait_for_http_health,
    wait_for_user_service_health,
)
from backend.deploy.strategies import get_registry, get_strategy
from backend.deploy.strategies.base import DeploymentContext
from backend.deploy.strategies.registry import DeploymentStrategyRegistry
from backend.deploy.strategies.verified import (
    VerifiedExpressStrategy,
    VerifiedFastAPIStrategy,
    VerifiedReactStaticStrategy,
    VerifiedSpringBootJarStrategy,
)
from backend.deploy.ssh import SSHClient
from unittest.mock import MagicMock, Mock, patch


class MockSSHClient:
    """Mock SSH client for testing"""
    
    def __init__(self):
        self.executed_commands = []
    
    def execute_command(self, command: str, use_pty: bool = False):
        self.executed_commands.append(command)
        return True, "", ""
    
    def upload_file(self, local_path: str, remote_path: str):
        return True, ""
    
    def upload_directory(self, local_path: str, remote_path: str):
        return True, ""


class VerifiedMockSSHClient(MockSSHClient):
    def __init__(
        self,
        *,
        previous_release: str | None = None,
        health_success: bool = True,
    ):
        super().__init__()
        self.uploaded_files = []
        self.uploaded_directories = []
        self.previous_release = previous_release
        self.health_success = health_success

    def execute_command(self, command: str, use_pty: bool = False):
        self.executed_commands.append(command)
        if command.startswith("readlink "):
            if self.previous_release:
                return True, f"{self.previous_release}\n", ""
            return False, "", ""
        if "curl --fail" in command and not self.health_success:
            return False, "", "unhealthy"
        if "is-active" in command:
            return True, "active\n", ""
        return True, "", ""

    def upload_file(self, local_path: str, remote_path: str):
        self.uploaded_files.append((local_path, remote_path))
        return True, ""

    def upload_directory(self, local_path: str, remote_path: str):
        self.uploaded_directories.append((local_path, remote_path))
        return True, ""


class TestDeploymentStrategySelection:
    """Test that strategy selection is based on framework/runtime metadata only"""
    
    def test_java_spring_boot_jar_strategy(self):
        """Test Spring Boot JAR strategy selection"""
        strategy = get_strategy("Spring Boot", "Java")
        assert strategy is not None
        assert strategy.name == "Spring Boot JAR"
        assert strategy.can_handle("Spring Boot", "Java")
        assert not strategy.can_handle("Express", "Node.js")
    
    def test_java_spring_boot_war_strategy(self):
        """Test Spring Boot WAR strategy selection"""
        strategy = get_strategy("Spring Boot", "Java")
        # Should return SpringBootJarStrategy first, but SpringBootWarStrategy also handles Spring Boot
        assert strategy is not None
        assert "Spring Boot" in strategy.name
    
    def test_java_jakarta_ee_strategy(self):
        """Test Jakarta EE strategy selection"""
        strategy = get_strategy("Jakarta EE", "Java")
        assert strategy is not None
        assert strategy.name == "Jakarta EE"
        assert strategy.can_handle("Jakarta EE", "Java")
    
    def test_java_quarkus_strategy(self):
        """Test Quarkus strategy selection"""
        strategy = get_strategy("Quarkus", "Java")
        assert strategy is not None
        assert strategy.name == "Quarkus"
        assert strategy.can_handle("Quarkus", "Java")
    
    def test_java_micronaut_strategy(self):
        """Test Micronaut strategy selection"""
        strategy = get_strategy("Micronaut", "Java")
        assert strategy is not None
        assert strategy.name == "Micronaut"
        assert strategy.can_handle("Micronaut", "Java")
    
    def test_java_servlet_jsp_strategy(self):
        """Test Java Servlet/JSP strategy selection"""
        strategy = get_strategy("Java Servlet/JSP", "Java")
        assert strategy is not None
        # Should be handled by SpringBootWarStrategy
        assert strategy.can_handle("Java Servlet/JSP", "Java")
    
    def test_nodejs_express_strategy(self):
        """Test Express strategy selection"""
        strategy = get_strategy("Express", "Node.js")
        assert strategy is not None
        assert strategy.name == "Express"
        assert strategy.can_handle("Express", "Node.js")
        assert not strategy.can_handle("Django", "Python")
    
    def test_nodejs_nestjs_strategy(self):
        """Test NestJS strategy selection"""
        strategy = get_strategy("NestJS", "Node.js")
        assert strategy is not None
        assert strategy.name == "NestJS"
        assert strategy.can_handle("NestJS", "Node.js")
    
    def test_nodejs_nextjs_strategy(self):
        """Test Next.js strategy selection"""
        strategy = get_strategy("Next.js", "Node.js")
        assert strategy is not None
        assert strategy.name == "Next.js"
        assert strategy.can_handle("Next.js", "Node.js")
    
    def test_nodejs_nuxt_strategy(self):
        """Test Nuxt strategy selection"""
        strategy = get_strategy("Nuxt", "Node.js")
        assert strategy is not None
        assert strategy.name == "Nuxt"
        assert strategy.can_handle("Nuxt", "Node.js")
    
    def test_python_django_strategy(self):
        """Test Django strategy selection"""
        strategy = get_strategy("Django", "Python")
        assert strategy is not None
        assert strategy.name == "Django"
        assert strategy.can_handle("Django", "Python")
        assert not strategy.can_handle("Express", "Node.js")
    
    def test_python_fastapi_strategy(self):
        """Test FastAPI strategy selection"""
        strategy = get_strategy("FastAPI", "Python")
        assert strategy is not None
        assert strategy.name == "FastAPI"
        assert strategy.can_handle("FastAPI", "Python")
    
    def test_python_flask_strategy(self):
        """Test Flask strategy selection"""
        strategy = get_strategy("Flask", "Python")
        assert strategy is not None
        assert strategy.name == "Flask"
        assert strategy.can_handle("Flask", "Python")
    
    def test_python_sanic_strategy(self):
        """Test Sanic strategy selection"""
        strategy = get_strategy("Sanic", "Python")
        assert strategy is not None
        assert strategy.name == "Sanic"
        assert strategy.can_handle("Sanic", "Python")
    
    def test_php_laravel_strategy(self):
        """Test Laravel strategy selection"""
        strategy = get_strategy("Laravel", "PHP")
        assert strategy is not None
        assert strategy.name == "Laravel"
        assert strategy.can_handle("Laravel", "PHP")
        assert not strategy.can_handle("Django", "Python")
    
    def test_php_symfony_strategy(self):
        """Test Symfony strategy selection"""
        strategy = get_strategy("Symfony", "PHP")
        assert strategy is not None
        assert strategy.name == "Symfony"
        assert strategy.can_handle("Symfony", "PHP")
    
    def test_php_codeigniter_strategy(self):
        """Test CodeIgniter strategy selection"""
        strategy = get_strategy("CodeIgniter", "PHP")
        assert strategy is not None
        assert strategy.name == "CodeIgniter"
        assert strategy.can_handle("CodeIgniter", "PHP")
    
    def test_dotnet_aspnet_core_strategy(self):
        """Test ASP.NET Core strategy selection"""
        strategy = get_strategy("ASP.NET Core", ".NET")
        assert strategy is not None
        assert strategy.name == "ASP.NET Core"
        assert strategy.can_handle("ASP.NET Core", ".NET")
        assert not strategy.can_handle("Django", "Python")
    
    def test_dotnet_blazor_strategy(self):
        """Test Blazor strategy selection"""
        strategy = get_strategy("Blazor", ".NET")
        assert strategy is not None
        assert strategy.name == "Blazor"
        assert strategy.can_handle("Blazor", ".NET")
    
    def test_go_strategy(self):
        """Test Go strategy selection"""
        strategy = get_strategy("Gin", "Go")
        # Go strategy handles all Go frameworks
        assert strategy is not None
        assert strategy.name == "Go"
        assert strategy.can_handle("Gin", "Go")
        assert strategy.can_handle("Fiber", "Go")
        assert not strategy.can_handle("Express", "Node.js")
    
    def test_rust_strategy(self):
        """Test Rust strategy selection"""
        strategy = get_strategy("Actix Web", "Rust")
        # Rust strategy handles all Rust frameworks
        assert strategy is not None
        assert strategy.name == "Rust"
        assert strategy.can_handle("Actix Web", "Rust")
        assert strategy.can_handle("Rocket", "Rust")
        assert not strategy.can_handle("Express", "Node.js")
    
    def test_ruby_rails_strategy(self):
        """Test Rails strategy selection"""
        strategy = get_strategy("Rails", "Ruby")
        assert strategy is not None
        assert strategy.name == "Ruby on Rails"
        assert strategy.can_handle("Rails", "Ruby")
        assert strategy.can_handle("Ruby on Rails", "Ruby")
        assert not strategy.can_handle("Django", "Python")
    
    def test_ruby_sinatra_strategy(self):
        """Test Sinatra strategy selection"""
        strategy = get_strategy("Sinatra", "Ruby")
        assert strategy is not None
        assert strategy.name == "Sinatra"
        assert strategy.can_handle("Sinatra", "Ruby")
    
    def test_elixir_phoenix_strategy(self):
        """Test Phoenix strategy selection"""
        strategy = get_strategy("Phoenix", "Elixir")
        assert strategy is not None
        assert strategy.name == "Phoenix"
        assert strategy.can_handle("Phoenix", "Elixir")
        assert not strategy.can_handle("Django", "Python")
    
    def test_static_hugo_strategy(self):
        """Test Hugo strategy selection"""
        strategy = get_strategy("Hugo", "Static")
        assert strategy is not None
        assert strategy.name == "Hugo"
        assert strategy.can_handle("Hugo", "Static")
        assert not strategy.can_handle("Django", "Python")
    
    def test_static_jekyll_strategy(self):
        """Test Jekyll strategy selection"""
        strategy = get_strategy("Jekyll", "Static")
        assert strategy is not None
        assert strategy.name == "Jekyll"
        assert strategy.can_handle("Jekyll", "Static")
    
    def test_static_gatsby_strategy(self):
        """Test Gatsby strategy selection"""
        strategy = get_strategy("Gatsby", "Static")
        assert strategy is not None
        assert strategy.name == "Gatsby"
        assert strategy.can_handle("Gatsby", "Static")
    
    def test_static_astro_strategy(self):
        """Test Astro strategy selection"""
        strategy = get_strategy("Astro", "Static")
        assert strategy is not None
        assert strategy.name == "Astro"
        assert strategy.can_handle("Astro", "Static")
    
    def test_static_docusaurus_strategy(self):
        """Test Docusaurus strategy selection"""
        strategy = get_strategy("Docusaurus", "Static")
        assert strategy is not None
        assert strategy.name == "Docusaurus"
        assert strategy.can_handle("Docusaurus", "Static")
    
    def test_static_mkdocs_strategy(self):
        """Test MkDocs strategy selection"""
        strategy = get_strategy("MkDocs", "Static")
        assert strategy is not None
        assert strategy.name == "MkDocs"
        assert strategy.can_handle("MkDocs", "Static")


class TestInvalidFrameworkCases:
    """Test that invalid/unknown frameworks are handled correctly"""
    
    def test_unknown_framework_returns_none(self):
        """Test that unknown framework returns None"""
        strategy = get_strategy("UnknownFramework", "UnknownRuntime")
        assert strategy is None
    
    def test_mismatched_framework_runtime(self):
        """Test that mismatched framework/runtime returns None"""
        strategy = get_strategy("Django", "Node.js")
        assert strategy is None
    
    def test_none_framework_returns_none(self):
        """Test that None framework returns None"""
        strategy = get_strategy(None, "Python")
        assert strategy is None
    
    def test_none_runtime_returns_none(self):
        """Test that None runtime returns None"""
        strategy = get_strategy("Django", None)
        assert strategy is None
    
    def test_both_none_returns_none(self):
        """Test that both None returns None"""
        strategy = get_strategy(None, None)
        assert strategy is None


class TestArtifactMismatchCases:
    """Test that artifact type mismatches are handled correctly"""
    
    def test_java_strategy_with_war_file(self):
        """Test Java WAR strategy with WAR file"""
        strategy = get_strategy("Java Servlet/JSP", "Java")
        assert strategy is not None
        
        mock_ssh = MockSSHClient()
        context = DeploymentContext(
            ssh_client=mock_ssh,
            deploy_path="/var/lib/tomcat9/webapps",
            service_name="tomcat9",
            artifact_path="/path/to/app.war",
            artifact_type="war",
            project_name="ROOT"
        )
        
        # Strategy should handle WAR file
        assert strategy.can_handle("Java Servlet/JSP", "Java")
    
    def test_java_strategy_with_directory(self):
        """Test Java WAR strategy with directory artifact"""
        strategy = get_strategy("Java Servlet/JSP", "Java")
        assert strategy is not None
        
        mock_ssh = MockSSHClient()
        context = DeploymentContext(
            ssh_client=mock_ssh,
            deploy_path="/var/lib/tomcat9/webapps",
            service_name="tomcat9",
            artifact_path="/path/to/project",
            artifact_type="directory",
            project_name="ROOT"
        )
        
        # Strategy should handle directory and search for WAR
        assert strategy.can_handle("Java Servlet/JSP", "Java")
    
    def test_nodejs_strategy_not_affected_by_java_war(self):
        """Test that Node.js strategy is not affected by Java WAR logic"""
        nodejs_strategy = get_strategy("Express", "Node.js")
        java_strategy = get_strategy("Java Servlet/JSP", "Java")
        
        assert nodejs_strategy is not None
        assert java_strategy is not None
        
        # Node.js strategy should not handle Java frameworks
        assert not nodejs_strategy.can_handle("Java Servlet/JSP", "Java")
        assert not nodejs_strategy.can_handle("Spring Boot", "Java")
        
        # Java strategy should not handle Node.js frameworks
        assert not java_strategy.can_handle("Express", "Node.js")
        assert not java_strategy.can_handle("Next.js", "Node.js")
    
    def test_python_strategy_not_affected_by_java_war(self):
        """Test that Python strategy is not affected by Java WAR logic"""
        python_strategy = get_strategy("Django", "Python")
        java_strategy = get_strategy("Java Servlet/JSP", "Java")
        
        assert python_strategy is not None
        assert java_strategy is not None
        
        # Python strategy should not handle Java frameworks
        assert not python_strategy.can_handle("Java Servlet/JSP", "Java")
        assert not python_strategy.can_handle("Spring Boot", "Java")
        
        # Java strategy should not handle Python frameworks
        assert not java_strategy.can_handle("Django", "Python")
        assert not java_strategy.can_handle("FastAPI", "Python")


class TestStrategyIsolation:
    """Test that strategies are isolated from each other"""
    
    def test_registry_contains_all_strategies(self):
        """Test that registry contains all expected strategies"""
        registry = get_registry()
        strategies = registry.list_strategies()
        
        strategy_names = [s["name"] for s in strategies]
        
        # Check for Java strategies
        assert "Spring Boot JAR" in strategy_names
        assert "Spring Boot WAR" in strategy_names
        assert "Jakarta EE" in strategy_names
        assert "Quarkus" in strategy_names
        assert "Micronaut" in strategy_names
        
        # Check for Node.js strategies
        assert "Express" in strategy_names
        assert "NestJS" in strategy_names
        assert "Next.js" in strategy_names
        assert "Nuxt" in strategy_names
        
        # Check for Python strategies
        assert "Django" in strategy_names
        assert "FastAPI" in strategy_names
        assert "Flask" in strategy_names
        assert "Sanic" in strategy_names
        
        # Check for PHP strategies
        assert "Laravel" in strategy_names
        assert "Symfony" in strategy_names
        assert "CodeIgniter" in strategy_names
        
        # Check for .NET strategies
        assert "ASP.NET Core" in strategy_names
        assert "Blazor" in strategy_names
        
        # Check for Go, Rust, Ruby, Elixir strategies
        assert "Go" in strategy_names
        assert "Rust" in strategy_names
        assert "Ruby on Rails" in strategy_names
        assert "Sinatra" in strategy_names
        assert "Phoenix" in strategy_names
        
        # Check for static site strategies
        assert "Hugo" in strategy_names
        assert "Jekyll" in strategy_names
        assert "Gatsby" in strategy_names
        assert "Astro" in strategy_names
        assert "Docusaurus" in strategy_names
        assert "MkDocs" in strategy_names
    
    def test_strategy_selection_order_consistent(self):
        """Test that strategy selection order is consistent"""
        # Get strategy multiple times
        strategy1 = get_strategy("Django", "Python")
        strategy2 = get_strategy("Django", "Python")
        strategy3 = get_strategy("Django", "Python")
        
        # Should return the same strategy type each time
        assert strategy1.name == strategy2.name == strategy3.name
    
    def test_adding_strategy_doesnt_affect_others(self):
        """Test that adding a new strategy doesn't affect existing ones"""
        # Get existing strategies
        django_strategy = get_strategy("Django", "Python")
        express_strategy = get_strategy("Express", "Node.js")
        
        # They should work before any hypothetical new strategy is added
        assert django_strategy is not None
        assert express_strategy is not None
        assert django_strategy.can_handle("Django", "Python")
        assert express_strategy.can_handle("Express", "Node.js")
        
        # The registry should be a singleton, so we get the same instance
        registry = get_registry()
        initial_count = len(registry._strategies)
        
        # Registry should have consistent number of strategies
        assert initial_count > 0


class TestStrategyDefaultPaths:
    """Test that each strategy provides appropriate default paths"""
    
    def test_java_default_paths(self):
        """Test Java strategies provide appropriate default paths"""
        war_strategy = get_strategy("Java Servlet/JSP", "Java")
        assert war_strategy is not None
        
        deploy_path = war_strategy.get_default_deploy_path("MyApp")
        service_name = war_strategy.get_default_service_name("MyApp")
        
        assert "/var/lib/tomcat9/webapps" in deploy_path or "/opt/" in deploy_path
        assert service_name is not None
    
    def test_nodejs_default_paths(self):
        """Test Node.js strategies provide appropriate default paths"""
        express_strategy = get_strategy("Express", "Node.js")
        assert express_strategy is not None
        
        deploy_path = express_strategy.get_default_deploy_path("MyApp")
        service_name = express_strategy.get_default_service_name("MyApp")
        
        assert "/var/www/" in deploy_path
        assert service_name is not None

    def test_python_default_paths(self):
        """Test Python strategies provide appropriate default paths"""
        django_strategy = get_strategy("Django", "Python")
        assert django_strategy is not None

        deploy_path = django_strategy.get_default_deploy_path("MyApp")
        service_name = django_strategy.get_default_service_name("MyApp")

        assert "/var/www/" in deploy_path
        assert service_name is not None


class TestDeploymentCapabilities:
    def test_verified_profiles_are_explicit(self):
        capabilities = DeploymentStrategyRegistry(
            enable_experimental=False
        ).list_capabilities()
        verified_names = {
            capability["name"]
            for capability in capabilities
            if capability["tier"] == "verified"
        }
        assert verified_names == {
            "Docker",
            "Express",
            "FastAPI",
            "React/Vite Static",
            "Spring Boot JAR",
        }

    def test_experimental_strategy_is_disabled_by_default(self):
        resolution = DeploymentStrategyRegistry(
            enable_experimental=False
        ).resolve_strategy("Django", "Python", "directory")
        assert resolution.status == "experimental_disabled"
        assert resolution.strategy.name == "Django"

    def test_experimental_strategy_can_be_enabled_explicitly(self):
        resolution = DeploymentStrategyRegistry(
            enable_experimental=True
        ).resolve_strategy("Django", "Python", "directory")
        assert resolution.status == "experimental_enabled"

    def test_artifact_type_disambiguates_spring_boot(self):
        registry = DeploymentStrategyRegistry(enable_experimental=False)
        jar_resolution = registry.resolve_strategy(
            "Spring Boot",
            "Java",
            "jar",
        )
        war_resolution = registry.resolve_strategy(
            "Spring Boot",
            "Java",
            "war",
        )
        assert jar_resolution.status == "verified"
        assert jar_resolution.strategy.name == "Spring Boot JAR"
        assert war_resolution.status == "experimental_disabled"
        assert war_resolution.strategy.name == "Spring Boot WAR"

    def test_artifact_mismatch_is_reported(self):
        resolution = DeploymentStrategyRegistry(
            enable_experimental=False
        ).resolve_strategy("FastAPI", "Python", "jar")
        assert resolution.status == "artifact_mismatch"
        assert resolution.expected_artifact_types == ["directory"]


class TestDeploymentInputSafety:
    @pytest.mark.parametrize(
        "deploy_path",
        [
            "/",
            "relative/path",
            "/srv/../etc",
            "/srv/app;rm",
            "/srv/app path",
        ],
    )
    def test_unsafe_deploy_paths_are_rejected(self, deploy_path):
        with pytest.raises(DeploymentSafetyError):
            validate_remote_deploy_path(deploy_path)

    def test_safe_deploy_path_is_normalized(self):
        assert validate_remote_deploy_path("/srv/apps/demo/") == (
            "/srv/apps/demo"
        )

    def test_unsafe_service_name_is_rejected(self):
        with pytest.raises(DeploymentSafetyError):
            validate_identifier("demo;restart", "Service name")


class TestSSHHostVerification:
    def test_reject_policy_and_known_hosts_are_required(self, tmp_path):
        known_hosts = tmp_path / "known_hosts"
        known_hosts.write_text("test-host-key", encoding="utf-8")
        paramiko_client = MagicMock()

        with patch(
            "backend.deploy.ssh.paramiko.SSHClient",
            return_value=paramiko_client,
        ):
            client = SSHClient(
                host="127.0.0.1",
                username="deploy",
                password="not-logged",
                known_hosts_path=str(known_hosts),
            )
            success, error = client.connect()

        assert success, error
        paramiko_client.load_system_host_keys.assert_called_once_with(
            str(known_hosts)
        )
        policy = paramiko_client.set_missing_host_key_policy.call_args.args[0]
        assert policy.__class__.__name__ == "RejectPolicy"

    def test_missing_known_hosts_file_blocks_connection(self, tmp_path):
        client = SSHClient(
            host="127.0.0.1",
            username="deploy",
            password="not-logged",
            known_hosts_path=str(tmp_path / "missing"),
        )
        success, error = client.connect()

        assert not success
        assert "known_hosts file not found" in error


class TestVerifiedStrategyExecution:
    def test_http_readiness_uses_bounded_remote_retries(self):
        ssh = VerifiedMockSSHClient()

        assert wait_for_http_health(ssh, 8080, "/health")
        assert "--retry 29" in ssh.executed_commands[-1]
        assert "--retry-max-time 30" in ssh.executed_commands[-1]

    def test_user_service_readiness_checks_service_before_http(self):
        ssh = VerifiedMockSSHClient()

        assert wait_for_user_service_health(
            ssh,
            "demo-service",
            8080,
            "/health",
        )
        assert "seq 1 30" in ssh.executed_commands[-2]
        assert "systemctl --user is-active --quiet" in (
            ssh.executed_commands[-2]
        )
        assert "curl --fail" in ssh.executed_commands[-1]

    @pytest.mark.parametrize(
        (
            "strategy",
            "artifact_name",
            "artifact_type",
            "service_name",
            "health_port",
        ),
        [
            (
                VerifiedExpressStrategy(),
                "express",
                "directory",
                "express-app",
                3000,
            ),
            (
                VerifiedFastAPIStrategy(),
                "fastapi",
                "directory",
                "fastapi-app",
                8000,
            ),
            (
                VerifiedSpringBootJarStrategy(),
                "demo.jar",
                "jar",
                "spring-app",
                8080,
            ),
            (
                VerifiedReactStaticStrategy(),
                "dist",
                "directory",
                "nginx",
                8081,
            ),
        ],
    )
    def test_verified_profile_executes_and_validates(
        self,
        tmp_path,
        strategy,
        artifact_name,
        artifact_type,
        service_name,
        health_port,
    ):
        artifact = tmp_path / artifact_name
        if artifact_type == "directory":
            artifact.mkdir()
        else:
            artifact.write_bytes(b"jar")

        if isinstance(strategy, VerifiedExpressStrategy):
            (artifact / "package.json").write_text(
                json.dumps({"scripts": {"start": "node app.js"}}),
                encoding="utf-8",
            )
            (artifact / "package-lock.json").write_text(
                "{}",
                encoding="utf-8",
            )
            (artifact / "app.js").write_text("", encoding="utf-8")
        elif isinstance(strategy, VerifiedFastAPIStrategy):
            (artifact / "main.py").write_text("", encoding="utf-8")
            (artifact / "requirements.txt").write_text(
                "fastapi==0.100.0\nuvicorn==0.22.0\n",
                encoding="utf-8",
            )
        elif isinstance(strategy, VerifiedReactStaticStrategy):
            (artifact / "index.html").write_text(
                "<main>ok</main>",
                encoding="utf-8",
            )

        ssh = VerifiedMockSSHClient()
        context = DeploymentContext(
            ssh_client=ssh,
            deploy_path=f"/srv/{service_name}",
            service_name=service_name,
            artifact_path=str(artifact),
            artifact_type=artifact_type,
            project_name="demo",
            workspace_dir=str(tmp_path),
            release_id="42",
            health_check_port=health_port,
        )

        assert strategy.execute(context, lambda _: None)
        assert strategy.validate(context, lambda _: None)
        assert any("/current" in command for command in ssh.executed_commands)
        assert any(
            "curl --fail" in command
            for command in ssh.executed_commands
        )

    def test_failed_health_check_rolls_back(self, tmp_path):
        artifact = tmp_path / "dist"
        artifact.mkdir()
        (artifact / "index.html").write_text("ok", encoding="utf-8")
        ssh = VerifiedMockSSHClient(
            previous_release="/srv/react/releases/old",
            health_success=False,
        )
        context = DeploymentContext(
            ssh_client=ssh,
            deploy_path="/srv/react",
            service_name="nginx",
            artifact_path=str(artifact),
            artifact_type="directory",
            workspace_dir=str(tmp_path),
            release_id="43",
            health_check_port=8081,
        )
        strategy = VerifiedReactStaticStrategy()

        assert strategy.execute(context, lambda _: None)
        assert not strategy.validate(context, lambda _: None)
        assert any(
            ".rollback" in command
            and "/srv/react/releases/old" in command
            for command in ssh.executed_commands
        )

    def test_fastapi_requires_pinned_dependencies(self, tmp_path):
        artifact = tmp_path / "fastapi"
        artifact.mkdir()
        (artifact / "main.py").write_text("", encoding="utf-8")
        (artifact / "requirements.txt").write_text(
            "fastapi>=0.100\n",
            encoding="utf-8",
        )
        context = DeploymentContext(
            ssh_client=VerifiedMockSSHClient(),
            deploy_path="/srv/fastapi",
            service_name="fastapi-app",
            artifact_path=str(artifact),
            artifact_type="directory",
            workspace_dir=str(tmp_path),
            release_id="44",
        )

        assert not VerifiedFastAPIStrategy().execute(
            context,
            lambda _: None,
        )

    def test_multiple_spring_jars_are_rejected(self, tmp_path):
        project = tmp_path / "project"
        target = project / "target"
        target.mkdir(parents=True)
        (target / "one.jar").write_bytes(b"one")
        (target / "two.jar").write_bytes(b"two")
        runner = BuildRunner(
            str(tmp_path / "workspace"),
            str(tmp_path / "logs"),
        )

        with pytest.raises(ValueError, match="Multiple deployable JAR"):
            runner.detect_artifact(
                str(project),
                str(tmp_path / "artifact.log"),
            )
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
