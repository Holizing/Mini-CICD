"""
Regression tests for deployment strategy selection and execution.
Tests ensure that strategy selection is based on framework/runtime metadata only,
and that modifying one strategy does not affect others.
"""
import pytest
from backend.deploy.strategies import get_strategy, get_registry
from backend.deploy.strategies.base import DeploymentContext
from unittest.mock import Mock, MagicMock


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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
