from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.common.database import Base, engine
from backend.project import router as project_router


Base.metadata.create_all(bind=engine)

app = FastAPI(title="Mini CI/CD API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(project_router)


@app.get("/")
async def root():
    return {"message": "Mini CI/CD API is running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
