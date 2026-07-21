# Mini-CICD

A lightweight CI/CD system for automated build and deployment of web applications across multiple frameworks.

## Features
- **Multi-Framework**: Supports Java, Node.js, Python, PHP, .NET, Go, Rust, Ruby, Elixir, and Static Sites.
- **Auto-Detection**: Automatically identifies frameworks, runtimes, and build tools.
- **Deploy Options**: Deploy from source code or via Docker containers.
- **Security**: Secure SSH deployment via password or SSH key.
- **Real-Time Logs**: Live monitoring for build and deployment stages.

## Architecture
- **Frontend**: React + Vite
- **Backend**: FastAPI
- **Database**: SQLite

## Quick Start
**Prerequisites:** Python 3.8+, Node.js 16+, Git.

**Backend (Port 8000):**
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

**Frontend (Port 5173):**
```bash
cd frontend
npm install
npm run dev
```

## License
MIT License. Pull Requests are welcome.
