# Mini-CICD

Mini-CICD is a small Linux-focused platform for managing repositories and
running Build -> Deploy workflows from a web interface.

GitHub push webhooks can start the same Project -> Build -> Deploy pipeline.
Each Project has an explicit automation profile, and deployment credentials
come from one global Linux target configuration.

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

## Manual test gate

Tests run locally and do not use GitHub Actions. They always create a temporary
SQLite database, so `backend/cicd.db` and the Ubuntu runtime database are never
modified.

```powershell
python -m pip install -r backend\requirements-dev.txt
python -m pytest backend\tests
python -m compileall backend
python -m pip check
cd frontend
npm ci
npm run build
```

The complete release and Ubuntu E2E checklist is in
`docs/RELEASE_CHECKLIST.md`.

## Security defaults

- Experimental strategies are off unless
  `MINI_CICD_ENABLE_EXPERIMENTAL_STRATEGIES=true`.
- SSH requires a trusted `known_hosts` file; unknown host keys are rejected.
- GitHub webhooks require `X-Hub-Signature-256` HMAC verification and use
  `X-GitHub-Delivery` as an idempotency key.
- New webhook secrets must contain 32 to 255 characters. Leaving the Settings
  input blank preserves the existing secret.
- Deployment target settings store only SSH key and `known_hosts` paths, never
  passwords or private key contents.
- Database files, runtime data, JWT secrets, SSH keys, logs and environment
  files must not be committed.
