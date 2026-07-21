import os
import re
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class DetectionResult:
    """Result of project detection"""
    framework: Optional[str] = None
    runtime: Optional[str] = None
    build_tool: Optional[str] = None
    packaging: Optional[str] = None
    recommended_deploy_script: Optional[str] = None
    recommended_deploy_path: Optional[str] = None
    recommended_service_name: Optional[str] = None
    confidence: float = 0.0


class ProjectDetector:
    """
    Modular project detection engine for deployment recommendations.
    
    Detects project type, framework, runtime, build tool, and packaging
    from repository structure and build artifacts.
    """
    
    def __init__(self, project_path: str):
        self.project_path = project_path
    
    def detect(self) -> DetectionResult:
        """
        Detect project type and generate deployment recommendations.
        
        Returns:
            DetectionResult with detected metadata and recommendations
        """
        # Try each detector in order of specificity
        detectors = [
            self._detect_java,
            self._detect_nodejs,
            self._detect_python,
            self._detect_dotnet,
            self._detect_go,
            self._detect_ruby,
            self._detect_php,
            self._detect_rust,
        ]
        
        best_result = DetectionResult()
        best_confidence = 0.0
        
        for detector in detectors:
            result = detector()
            if result and result.confidence > best_confidence:
                best_result = result
                best_confidence = result.confidence
        
        return best_result
    
    def _detect_java(self) -> Optional[DetectionResult]:
        """Detect Java projects (Spring Boot, Maven, Gradle)"""
        result = DetectionResult()
        
        # Check for pom.xml (Maven)
        pom_path = os.path.join(self.project_path, 'pom.xml')
        if os.path.exists(pom_path):
            result.build_tool = 'Maven'
            result.runtime = 'Java'
            result.confidence = 0.7
            
            # Read pom.xml to detect framework
            try:
                with open(pom_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                if 'spring-boot' in content.lower():
                    result.framework = 'Spring Boot'
                    result.confidence = 0.9
                    result.packaging = 'JAR'
                    result.recommended_deploy_path = '/var/lib/tomcat9/webapps'
                    result.recommended_service_name = 'tomcat9'
                    result.recommended_deploy_script = (
                        'sudo -n systemctl stop tomcat9\n'
                        'sudo -n rm -rf /var/lib/tomcat9/webapps/ROOT\n'
                        'sudo -n cp {artifact} /var/lib/tomcat9/webapps/ROOT.war\n'
                        'sudo -n systemctl start tomcat9'
                    )
                elif 'spring' in content.lower():
                    result.framework = 'Spring'
                    result.confidence = 0.8
                    result.packaging = 'WAR'
                    result.recommended_deploy_path = '/var/lib/tomcat9/webapps'
                    result.recommended_service_name = 'tomcat9'
                elif 'servlet' in content.lower() or 'jsp' in content.lower():
                    result.framework = 'Java Servlet/JSP'
                    result.confidence = 0.7
                    result.packaging = 'WAR'
                    result.recommended_deploy_path = '/var/lib/tomcat9/webapps'
                    result.recommended_service_name = 'tomcat9'
                    result.recommended_deploy_script = (
                        'sudo -n systemctl stop tomcat9\n'
                        'sudo -n rm -rf /var/lib/tomcat9/webapps/{artifact_name}\n'
                        'sudo -n cp {artifact} /var/lib/tomcat9/webapps/\n'
                        'sudo -n systemctl start tomcat9'
                    )
                elif 'quarkus' in content.lower():
                    result.framework = 'Quarkus'
                    result.confidence = 0.9
                    result.packaging = 'JAR'
                    result.recommended_deploy_path = '/opt/quarkus'
                    result.recommended_service_name = 'quarkus'
                elif 'micronaut' in content.lower():
                    result.framework = 'Micronaut'
                    result.confidence = 0.9
                    result.packaging = 'JAR'
            except Exception:
                pass
        
        # Check for build.gradle or build.gradle.kts (Gradle)
        gradle_path = os.path.join(self.project_path, 'build.gradle')
        gradle_kts_path = os.path.join(self.project_path, 'build.gradle.kts')
        
        if os.path.exists(gradle_path) or os.path.exists(gradle_kts_path):
            result.build_tool = 'Gradle'
            result.runtime = 'Java'
            result.confidence = max(result.confidence, 0.7)
            
            try:
                gradle_file = gradle_path if os.path.exists(gradle_path) else gradle_kts_path
                with open(gradle_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if 'spring-boot' in content.lower():
                    result.framework = 'Spring Boot'
                    result.confidence = 0.9
                    result.packaging = 'JAR'
                    result.recommended_deploy_path = '/var/lib/tomcat9/webapps'
                    result.recommended_service_name = 'tomcat9'
                elif 'quarkus' in content.lower():
                    result.framework = 'Quarkus'
                    result.confidence = 0.9
                    result.packaging = 'JAR'
            except Exception:
                pass
        
        return result if result.confidence > 0 else None
    
    def _detect_nodejs(self) -> Optional[DetectionResult]:
        """Detect Node.js projects (Express, NestJS, Next.js, React, Vue, etc.)"""
        result = DetectionResult()
        
        # Check for package.json
        package_json_path = os.path.join(self.project_path, 'package.json')
        if not os.path.exists(package_json_path):
            return None
        
        result.runtime = 'Node.js'
        result.confidence = 0.6
        
        try:
            with open(package_json_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Detect framework from dependencies
            dependencies_lower = content.lower()
            
            if '@nestjs/core' in dependencies_lower or '@nestjs/common' in dependencies_lower:
                result.framework = 'NestJS'
                result.confidence = 0.9
                result.build_tool = 'npm'
                result.recommended_deploy_path = '/var/www/nestjs'
                result.recommended_service_name = 'nestjs'
                result.recommended_deploy_script = (
                    'cd /var/www/nestjs\n'
                    'npm install --production\n'
                    'npm run build\n'
                    'pm2 restart nestjs || pm2 start dist/main.js --name nestjs'
                )
            elif 'next' in dependencies_lower:
                result.framework = 'Next.js'
                result.confidence = 0.9
                result.build_tool = 'npm'
                result.recommended_deploy_path = '/var/www/nextjs'
                result.recommended_service_name = 'nextjs'
                result.recommended_deploy_script = (
                    'cd /var/www/nextjs\n'
                    'npm install --production\n'
                    'npm run build\n'
                    'pm2 restart nextjs || pm2 start npm --name nextjs -- start'
                )
            elif 'express' in dependencies_lower:
                result.framework = 'Express'
                result.confidence = 0.85
                result.build_tool = 'npm'
                result.recommended_deploy_path = '/var/www/express'
                result.recommended_service_name = 'express'
                result.recommended_deploy_script = (
                    'cd /var/www/express\n'
                    'npm install --production\n'
                    'pm2 restart express || pm2 start app.js --name express'
                )
            elif 'react' in dependencies_lower:
                result.framework = 'React'
                result.confidence = 0.85
                result.build_tool = 'npm'
                result.packaging = 'Static'
                result.recommended_deploy_path = '/var/www/react'
                result.recommended_service_name = 'nginx'
                result.recommended_deploy_script = (
                    'cd /var/www/react\n'
                    'npm run build\n'
                    'sudo -n cp -r build/* /var/www/html/'
                )
            elif 'vue' in dependencies_lower:
                result.framework = 'Vue'
                result.confidence = 0.85
                result.build_tool = 'npm'
                result.packaging = 'Static'
                result.recommended_deploy_path = '/var/www/vue'
                result.recommended_service_name = 'nginx'
                result.recommended_deploy_script = (
                    'cd /var/www/vue\n'
                    'npm run build\n'
                    'sudo -n cp -r dist/* /var/www/html/'
                )
            elif '@angular/core' in dependencies_lower:
                result.framework = 'Angular'
                result.confidence = 0.9
                result.build_tool = 'npm'
                result.packaging = 'Static'
                result.recommended_deploy_path = '/var/www/angular'
                result.recommended_service_name = 'nginx'
            elif 'svelte' in dependencies_lower:
                result.framework = 'SvelteKit'
                result.confidence = 0.85
                result.build_tool = 'npm'
            elif 'astro' in dependencies_lower:
                result.framework = 'Astro'
                result.confidence = 0.85
                result.build_tool = 'npm'
                result.packaging = 'Static'
            elif 'remix' in dependencies_lower:
                result.framework = 'Remix'
                result.confidence = 0.85
                result.build_tool = 'npm'
            
            # Detect build tool from scripts
            if 'yarn' in content.lower():
                result.build_tool = 'yarn'
            elif 'pnpm' in content.lower():
                result.build_tool = 'pnpm'
            elif not result.build_tool:
                result.build_tool = 'npm'
                
        except Exception:
            pass
        
        return result if result.confidence > 0 else None
    
    def _detect_python(self) -> Optional[DetectionResult]:
        """Detect Python projects (FastAPI, Django, Flask, etc.)"""
        result = DetectionResult()
        
        # Check for Python files
        python_files = []
        for root, dirs, files in os.walk(self.project_path):
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'venv', 'node_modules'}]
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))
        
        if not python_files:
            return None
        
        result.runtime = 'Python'
        result.confidence = 0.5
        
        # Check for requirements.txt or pyproject.toml
        requirements_path = os.path.join(self.project_path, 'requirements.txt')
        pyproject_path = os.path.join(self.project_path, 'pyproject.toml')
        
        if os.path.exists(requirements_path):
            try:
                with open(requirements_path, 'r', encoding='utf-8') as f:
                    content = f.read().lower()
                
                if 'fastapi' in content:
                    result.framework = 'FastAPI'
                    result.confidence = 0.9
                    result.build_tool = 'pip'
                    result.recommended_deploy_path = '/var/www/fastapi'
                    result.recommended_service_name = 'fastapi'
                    result.recommended_deploy_script = (
                        'cd /var/www/fastapi\n'
                        'pip install -r requirements.txt\n'
                        'pm2 restart fastapi || pm2 start uvicorn main:app --name fastapi'
                    )
                elif 'django' in content:
                    result.framework = 'Django'
                    result.confidence = 0.9
                    result.build_tool = 'pip'
                    result.recommended_deploy_path = '/var/www/django'
                    result.recommended_service_name = 'gunicorn'
                    result.recommended_deploy_script = (
                        'cd /var/www/django\n'
                        'pip install -r requirements.txt\n'
                        'python manage.py migrate\n'
                        'pm2 restart gunicorn || pm2 start gunicorn config.wsgi --name gunicorn'
                    )
                elif 'flask' in content:
                    result.framework = 'Flask'
                    result.confidence = 0.85
                    result.build_tool = 'pip'
                    result.recommended_deploy_path = '/var/www/flask'
                    result.recommended_service_name = 'flask'
                    result.recommended_deploy_script = (
                        'cd /var/www/flask\n'
                        'pip install -r requirements.txt\n'
                        'pm2 restart flask || pm2 start app.py --name flask'
                    )
                elif 'sanic' in content:
                    result.framework = 'Sanic'
                    result.confidence = 0.85
                    result.build_tool = 'pip'
                elif 'tornado' in content:
                    result.framework = 'Tornado'
                    result.confidence = 0.85
                    result.build_tool = 'pip'
                else:
                    result.build_tool = 'pip'
            except Exception:
                pass
        
        elif os.path.exists(pyproject_path):
            result.build_tool = 'poetry'
            result.confidence = 0.7
        else:
            result.build_tool = 'pip'
        
        return result if result.confidence > 0 else None
    
    def _detect_dotnet(self) -> Optional[DetectionResult]:
        """Detect .NET projects (ASP.NET Core, Blazor)"""
        result = DetectionResult()
        
        # Check for .csproj files
        csproj_files = []
        for root, dirs, files in os.walk(self.project_path):
            dirs[:] = [d for d in dirs if d not in {'.git', 'bin', 'obj', 'node_modules'}]
            for file in files:
                if file.endswith('.csproj'):
                    csproj_files.append(os.path.join(root, file))
        
        if not csproj_files:
            return None
        
        result.runtime = '.NET'
        result.build_tool = 'dotnet'
        result.confidence = 0.7
        
        try:
            for csproj_file in csproj_files:
                with open(csproj_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if 'Microsoft.AspNetCore' in content:
                    result.framework = 'ASP.NET Core'
                    result.confidence = 0.9
                    result.packaging = 'DLL'
                    result.recommended_deploy_path = '/var/www/dotnet'
                    result.recommended_service_name = 'dotnet'
                    result.recommended_deploy_script = (
                        'cd /var/www/dotnet\n'
                        'dotnet publish -c Release\n'
                        'pm2 restart dotnet || pm2 start "dotnet ./publish/MyApp.dll" --name dotnet'
                    )
                    break
                elif 'blazor' in content.lower():
                    result.framework = 'Blazor'
                    result.confidence = 0.9
                    result.packaging = 'Static'
                    break
        except Exception:
            pass
        
        return result if result.confidence > 0 else None
    
    def _detect_go(self) -> Optional[DetectionResult]:
        """Detect Go projects (Gin, Fiber, Echo, etc.)"""
        result = DetectionResult()
        
        # Check for go.mod
        go_mod_path = os.path.join(self.project_path, 'go.mod')
        if not os.path.exists(go_mod_path):
            return None
        
        result.runtime = 'Go'
        result.build_tool = 'go'
        result.confidence = 0.7
        
        try:
            with open(go_mod_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if 'gin-gonic' in content:
                result.framework = 'Gin'
                result.confidence = 0.9
            elif 'gofiber' in content:
                result.framework = 'Fiber'
                result.confidence = 0.9
            elif 'labstack/echo' in content:
                result.framework = 'Echo'
                result.confidence = 0.9
            elif 'beego' in content:
                result.framework = 'Beego'
                result.confidence = 0.9
            elif 'go-chi' in content:
                result.framework = 'Chi'
                result.confidence = 0.9
            
            result.packaging = 'Binary'
            result.recommended_deploy_path = '/opt/go'
            result.recommended_service_name = 'goapp'
            result.recommended_deploy_script = (
                'cd /opt/go\n'
                'go build -o app\n'
                'pm2 restart goapp || pm2 start ./app --name goapp'
            )
        except Exception:
            pass
        
        return result if result.confidence > 0 else None
    
    def _detect_ruby(self) -> Optional[DetectionResult]:
        """Detect Ruby projects (Rails, Sinatra)"""
        result = DetectionResult()
        
        # Check for Gemfile
        gemfile_path = os.path.join(self.project_path, 'Gemfile')
        if not os.path.exists(gemfile_path):
            return None
        
        result.runtime = 'Ruby'
        result.build_tool = 'bundler'
        result.confidence = 0.7
        
        try:
            with open(gemfile_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if 'rails' in content.lower():
                result.framework = 'Rails'
                result.confidence = 0.9
                result.recommended_deploy_path = '/var/www/rails'
                result.recommended_service_name = 'puma'
                result.recommended_deploy_script = (
                    'cd /var/www/rails\n'
                    'bundle install\n'
                    'rails db:migrate\n'
                    'pm2 restart puma || puma -C config/puma.rb'
                )
            elif 'sinatra' in content.lower():
                result.framework = 'Sinatra'
                result.confidence = 0.85
        except Exception:
            pass
        
        return result if result.confidence > 0 else None
    
    def _detect_php(self) -> Optional[DetectionResult]:
        """Detect PHP projects (Laravel, Symfony, etc.)"""
        result = DetectionResult()
        
        # Check for composer.json
        composer_path = os.path.join(self.project_path, 'composer.json')
        if not os.path.exists(composer_path):
            return None
        
        result.runtime = 'PHP'
        result.build_tool = 'composer'
        result.confidence = 0.7
        
        try:
            with open(composer_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if 'laravel' in content.lower():
                result.framework = 'Laravel'
                result.confidence = 0.9
                result.recommended_deploy_path = '/var/www/laravel'
                result.recommended_service_name = 'php-fpm'
                result.recommended_deploy_script = (
                    'cd /var/www/laravel\n'
                    'composer install --no-dev\n'
                    'php artisan migrate\n'
                    'sudo -n systemctl reload php-fpm'
                )
            elif 'symfony' in content.lower():
                result.framework = 'Symfony'
                result.confidence = 0.9
            elif 'codeigniter' in content.lower():
                result.framework = 'CodeIgniter'
                result.confidence = 0.85
            elif 'cakephp' in content.lower():
                result.framework = 'CakePHP'
                result.confidence = 0.85
            elif 'yii' in content.lower():
                result.framework = 'Yii'
                result.confidence = 0.85
        except Exception:
            pass
        
        return result if result.confidence > 0 else None
    
    def _detect_rust(self) -> Optional[DetectionResult]:
        """Detect Rust projects (Actix Web, Rocket, Axum)"""
        result = DetectionResult()
        
        # Check for Cargo.toml
        cargo_path = os.path.join(self.project_path, 'Cargo.toml')
        if not os.path.exists(cargo_path):
            return None
        
        result.runtime = 'Rust'
        result.build_tool = 'cargo'
        result.confidence = 0.7
        
        try:
            with open(cargo_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if 'actix-web' in content:
                result.framework = 'Actix Web'
                result.confidence = 0.9
            elif 'rocket' in content:
                result.framework = 'Rocket'
                result.confidence = 0.9
            elif 'axum' in content:
                result.framework = 'Axum'
                result.confidence = 0.9
            
            result.packaging = 'Binary'
            result.recommended_deploy_path = '/opt/rust'
            result.recommended_service_name = 'rustapp'
            result.recommended_deploy_script = (
                'cd /opt/rust\n'
                'cargo build --release\n'
                'pm2 restart rustapp || pm2 start ./target/release/app --name rustapp'
            )
        except Exception:
            pass
        
        return result if result.confidence > 0 else None
