import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from backend.common.database import engine, Base
from backend.build import router as build_router
from backend.deploy import router as deploy_router

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Mini CI/CD API")

# Include routers
app.include_router(build_router)
app.include_router(deploy_router)


@app.get("/")
async def root():
    return {"message": "Mini CI/CD API is running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
