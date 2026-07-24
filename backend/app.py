import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.auth import router as auth_router
from backend.auth.dependencies import get_current_admin
from backend.build import router as build_router
from backend.common.config import get_cors_origins
from backend.common.database import Base, SessionLocal, engine
from backend.deploy import router as deploy_router
from backend.project import router as project_router
from backend.settings import router as settings_router
from backend.webhook import (
    protected_router as webhook_protected_router,
    public_router as webhook_public_router,
)
from backend.webhook.service import recover_interrupted_deliveries


Base.metadata.create_all(bind=engine)
with SessionLocal() as startup_db:
    recover_interrupted_deliveries(startup_db)

app = FastAPI(title="Mini CI/CD API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

protected = [Depends(get_current_admin)]

app.include_router(auth_router)
app.include_router(project_router, dependencies=protected)
app.include_router(settings_router)
app.include_router(build_router, dependencies=protected)
app.include_router(deploy_router, dependencies=protected)
app.include_router(webhook_public_router)
app.include_router(webhook_protected_router, dependencies=protected)


@app.get("/")
async def root():
    return {"message": "Mini CI/CD API is running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
