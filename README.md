# Mini-CICD

A lightweight CI/CD system for automated build and deployment of web applications across multiple frameworks.

## Overview

Mini-CICD provides automated build and deployment capabilities for various web frameworks with intelligent framework detection and strategy-based deployment. It supports both source code deployment and Docker container deployment.

### Key Features

- **Multi-Framework Support**: Java (Spring Boot, Jakarta EE, Quarkus, Micronaut), Node.js (Express, NestJS, Next.js, Nuxt), Python (Django, FastAPI, Flask, Sanic), PHP (Laravel, Symfony, CodeIgniter), .NET (ASP.NET Core, Blazor), Go, Rust, Ruby (Rails, Sinatra), Elixir (Phoenix), and static site generators (Hugo, Jekyll, Gatsby, Astro, Docusaurus, MkDocs)

- **Intelligent Framework Detection**: Automatically detects project framework, runtime, and build tool from source code

- **Strategy-Based Deployment**: Framework-specific deployment strategies ensure correct deployment for each technology stack

- **Docker Support**: Build from git or pull existing images from registry

- **SSH-Based Deployment**: Secure remote deployment via SSH with password or SSH key authentication

- **Deploy Script Recommendations**: Ghost text suggestions for custom deployment scripts (user can accept with Tab)

- **Real-Time Logs**: Live deployment logs with stage-by-stage progress tracking

- **Build History**: Track build and deployment history with status monitoring

## Architecture

```
┌─────────────────┐
│   Frontend     │ (React + Vite)
│   (UI)         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Backend       │ (FastAPI)
│   ┌───────────┐ │
│   │ Build     │ │ - Framework detection
│   │ Module    │ │ - Build execution
│   └───────────┘ │
│   ┌───────────┐ │
│   │ Deploy    │ │ - Strategy selection
│   │ Module    │ │ - SSH deployment
│   └───────────┘ │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Database      │ (SQLite)
│   (cicd.db)     │
└─────────────────┘
```

### Backend Modules

**Build Module** (`backend/build/`)
- `detector.py`: Framework detection from project files
- `runner.py`: Build execution for various frameworks
- `service.py`: Build orchestration and state management
- `models.py`: Build data models
- `router.py`: Build API endpoints

**Deploy Module** (`backend/deploy/`)
- `service.py`: Deployment orchestration
- `strategies/`: Framework-specific deployment strategies
- `ssh.py`: SSH client for remote operations
- `models.py`: Deploy data models
- `router.py`: Deploy API endpoints

## Installation

### Prerequisites

- Python 3.8+
- Node.js 16+ (for frontend)
- Git

### Backend Setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate  # On Windows
pip install -r requirements.txt
python app.py
```

Backend runs on `http://localhost:8000`

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on `http://localhost:5173`

## Usage

### 1. Create a Project

Navigate to the Projects page and create a new project by providing:
- Project name
- Git repository URL
- Branch (default: main)

### 2. Build a Project

1. Select a project from the Build page
2. Configure build settings (auto-detected from framework)
3. Click "Start Build"
4. Monitor build progress in real-time logs

### 3. Deploy a Build

1. Select a successful build from the Deploy page
2. Configure deployment settings:
   - **Server IP**: Target server address
   - **Server User**: SSH username
   - **Authentication**: Password or SSH key
   - **Deploy Type**: Source or Docker
3. For Source Deploy:
   - **Deploy Path**: Target directory on server
   - **Service Name**: System service name
   - **Deploy Script**: Optional custom script (ghost suggestion available)
4. For Docker Deploy:
   - **Docker Mode**: Build from git or existing image
   - **Container Name**: Container identifier
   - **Port Mapping**: Host:container port mapping
5. Click "Start Deploy" and monitor deployment logs

## Supported Frameworks

### Java
- Spring Boot (JAR/WAR)
- Jakarta EE
- Quarkus
- Micronaut
- Java Servlet/JSP

### Node.js
- Express
- NestJS
- Next.js
- Nuxt
- Static sites

### Python
- Django
- FastAPI
- Flask
- Sanic

### PHP
- Laravel
- Symfony
- CodeIgniter

### .NET
- ASP.NET Core
- Blazor

### Other
- Go (Gin, Fiber, etc.)
- Rust (Actix Web, Rocket, etc.)
- Ruby (Rails, Sinatra)
- Elixir (Phoenix)

### Static Sites
- Hugo
- Jekyll
- Gatsby
- Astro
- Docusaurus
- MkDocs

## Configuration

### Environment Variables

No environment variables required for basic operation. The system uses SQLite database (`cicd.db`) for data persistence.

### SSH Configuration

For password-based authentication, provide the server password in the deploy form.

For SSH key authentication, provide the path to the private key file (e.g., `C:/Users/you/.ssh/id_rsa`).

## API Endpoints

### Build API
- `POST /api/build/start` - Start a new build
- `GET /api/build/{build_id}` - Get build status
- `GET /api/build/history` - Get build history
- `GET /api/build/log/{build_id}` - Get build log

### Deploy API
- `POST /api/deploy/start` - Start a new deployment
- `GET /api/deploy/{deploy_id}` - Get deploy status
- `GET /api/deploy/history` - Get deploy history
- `GET /api/deploy/log/{deploy_id}` - Get deploy log
- `GET /api/deploy/stages/{deploy_id}` - Get deployment stages

### Project API
- `POST /api/projects` - Create a project
- `GET /api/projects` - List all projects
- `GET /api/projects/{project_id}` - Get project details

## Deployment Strategies

Each framework has a specific deployment strategy that handles:
- Artifact upload (JAR, WAR, tar.gz, etc.)
- Service management (systemctl, PM2, etc.)
- Dependency installation
- Configuration updates
- Health checks

Strategies are located in `backend/deploy/strategies/` and are automatically selected based on detected framework.

## Development

### Running Tests

```bash
cd backend
pytest tests/
```

### Adding New Framework Support

1. Add detection logic in `backend/build/detector.py`
2. Create deployment strategy in `backend/deploy/strategies/`
3. Register strategy in `backend/deploy/strategies/registry.py`
4. Add build runner logic in `backend/build/runner.py` if needed

## License

MIT License

## Contributing

Contributions are welcome! Please submit pull requests to the repository.

