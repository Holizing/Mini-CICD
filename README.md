# Mini-CICD

Mini-CICD is a small Linux-focused platform for managing repositories and
running Build -> Deploy workflows from a web interface.

## Verified deployment profiles

- Docker image build/deploy.
- React/Vite prebuilt static artifact.
- FastAPI source artifact with pinned Python dependencies.
- Express source artifact with `package-lock.json`.
- Spring Boot executable JAR.

Other strategy recipes remain available as **experimental** code. They are
disabled by default and must not be presented as verified support.

## Stack

- Backend: Python, FastAPI, Uvicorn, SQLAlchemy, SQLite, Paramiko.
- Frontend: React, Vite, React Router DOM, Axios.
- Linux runtime: systemd, Nginx, OpenSSH, Docker Engine.

## Local development

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
python -m uvicorn backend.app:app --reload
```

```powershell
cd frontend
npm ci
npm run dev
```

Open the API documentation at `http://127.0.0.1:8000/docs`. The Ubuntu staging
runbook is in `ops/linux/README.md`.

## Security defaults

- Experimental strategies are off unless
  `MINI_CICD_ENABLE_EXPERIMENTAL_STRATEGIES=true`.
- SSH requires a trusted `known_hosts` file; unknown host keys are rejected.
- Database files, runtime data, JWT secrets, SSH keys, logs and environment
  files must not be committed.
