from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.common.database import get_db
from backend.project.schemas import (
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
)
from backend.project.service import ProjectService


router = APIRouter(prefix="/projects", tags=["projects"])


def get_project_service(db: Session = Depends(get_db)) -> ProjectService:
    return ProjectService(db)


@router.get("", response_model=ProjectListResponse)
async def get_projects(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    project_service: ProjectService = Depends(get_project_service),
):
    projects, total = project_service.get_projects(limit=limit, offset=offset)
    return ProjectListResponse(projects=projects, total=total)


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    request: ProjectCreate,
    project_service: ProjectService = Depends(get_project_service),
):
    return project_service.create_project(request)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    project_service: ProjectService = Depends(get_project_service),
):
    project = project_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    request: ProjectUpdate,
    project_service: ProjectService = Depends(get_project_service),
):
    project = project_service.update_project(project_id, request)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    project_service: ProjectService = Depends(get_project_service),
):
    deleted = project_service.delete_project(project_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Project not found")
    return None
