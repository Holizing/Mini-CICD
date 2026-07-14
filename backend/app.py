from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.auth import router as auth_router
from backend.common.config import get_cors_origins
from backend.common.database import Base, engine
from backend.settings import router as settings_router


Base.metadata.create_all(bind=engine)

app = FastAPI(title="Mini CI/CD API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(settings_router)


@app.get("/")
async def root():
    return {"message": "Mini CI/CD API is running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
