from fastapi.testclient import TestClient

from backend.app import app


client = TestClient(app)


def project_payload(**overrides):
    payload = {
        "name": "demo-api",
        "repo_url": "https://github.com/demo/demo-api.git",
        "branch": "main",
        "description": "Demo project",
        "deploy_path": "/var/www/demo-api",
        "service_name": "demo-api",
        "status": "active",
    }
    payload.update(overrides)
    return payload


def test_project_crud_flow():
    created = client.post("/projects", json=project_payload(name="pytest-demo-api"))
    assert created.status_code == 201
    created_body = created.json()
    project_id = created_body["id"]

    listed = client.get("/projects")
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1

    fetched = client.get(f"/projects/{project_id}")
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "pytest-demo-api"

    updated = client.put(f"/projects/{project_id}", json={"branch": "dev"})
    assert updated.status_code == 200
    assert updated.json()["branch"] == "dev"

    deleted = client.delete(f"/projects/{project_id}")
    assert deleted.status_code == 204

    missing = client.get(f"/projects/{project_id}")
    assert missing.status_code == 404


def test_project_rejects_invalid_status():
    response = client.post("/projects", json=project_payload(status="archived"))
    assert response.status_code == 422


def test_project_rejects_relative_deploy_path():
    response = client.post("/projects", json=project_payload(deploy_path="relative/path"))
    assert response.status_code == 422


def test_project_rejects_unsupported_repo_url():
    response = client.post("/projects", json=project_payload(repo_url="ftp://example.com/repo.git"))
    assert response.status_code == 422
