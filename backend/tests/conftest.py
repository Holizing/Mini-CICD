import os
import shutil
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient


TEST_RUNTIME_ROOT = Path(tempfile.mkdtemp(prefix="mini-cicd-tests-"))
TEST_DATABASE_PATH = TEST_RUNTIME_ROOT / "cicd-test.db"
TEST_JWT_SECRET = "test-only-jwt-secret-with-at-least-32-characters"

_ORIGINAL_DATABASE_PATH = os.environ.get("MINI_CICD_DATABASE_PATH")
_ORIGINAL_JWT_SECRET = os.environ.get("MINI_CICD_JWT_SECRET")
os.environ["MINI_CICD_DATABASE_PATH"] = str(TEST_DATABASE_PATH)
os.environ["MINI_CICD_JWT_SECRET"] = TEST_JWT_SECRET

from backend.app import app
from backend.auth.dependencies import get_current_admin
from backend.common.database import Base, SessionLocal, engine


@pytest.fixture(scope="session", autouse=True)
def isolated_test_runtime():
    yield TEST_RUNTIME_ROOT
    engine.dispose()
    shutil.rmtree(TEST_RUNTIME_ROOT, ignore_errors=True)

    if _ORIGINAL_DATABASE_PATH is None:
        os.environ.pop("MINI_CICD_DATABASE_PATH", None)
    else:
        os.environ["MINI_CICD_DATABASE_PATH"] = _ORIGINAL_DATABASE_PATH

    if _ORIGINAL_JWT_SECRET is None:
        os.environ.pop("MINI_CICD_JWT_SECRET", None)
    else:
        os.environ["MINI_CICD_JWT_SECRET"] = _ORIGINAL_JWT_SECRET


@pytest.fixture
def clean_database(isolated_test_runtime):
    engine.dispose()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    workspace = isolated_test_runtime / "workspace"
    logs = isolated_test_runtime / "logs"
    artifact = isolated_test_runtime / "artifact"
    workspace.mkdir(exist_ok=True)
    logs.mkdir(exist_ok=True)
    artifact.mkdir(exist_ok=True)
    (artifact / "index.html").write_text("<h1>test</h1>", encoding="utf-8")

    yield isolated_test_runtime

    engine.dispose()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def api_client(clean_database):
    app.dependency_overrides[get_current_admin] = lambda: SimpleNamespace(
        id=1,
        username="test-admin",
        is_active=True,
    )
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_current_admin, None)


@pytest.fixture
def unauthenticated_client(clean_database):
    app.dependency_overrides.pop(get_current_admin, None)
    with TestClient(app) as client:
        yield client
