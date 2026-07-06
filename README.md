# Mini-CICD

## Project Management Module

This branch implements the project/repository management feature for the Mini CI/CD platform.

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cd ..
uvicorn backend.app:app --reload
```

Backend API:

- `GET /projects`
- `POST /projects`
- `GET /projects/{project_id}`
- `PUT /projects/{project_id}`
- `DELETE /projects/{project_id}`

Swagger UI is available at:

```text
http://localhost:8000/docs
```

Run backend tests:

```bash
pip install -r backend/requirements-dev.txt
pytest backend/tests
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend page:

```text
http://localhost:3000/projects
```
