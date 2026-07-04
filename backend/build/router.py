from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from backend.common.database import get_db
from backend.build.schemas import BuildStartRequest, BuildResponse, BuildHistoryResponse
from backend.build.service import BuildService


router = APIRouter(prefix="/build", tags=["build"])


def get_build_service(
    db: Session = Depends(get_db)
) -> BuildService:
    """
    Dependency to get BuildService instance.
    
    Args:
        db: Database session
        
    Returns:
        BuildService instance
    """
    # Configure these paths based on your project structure
    workspace_dir = "workspace"
    logs_dir = "logs"
    return BuildService(db, workspace_dir, logs_dir)


@router.post("/start", response_model=BuildResponse)
async def start_build(
    request: BuildStartRequest,
    build_service: BuildService = Depends(get_build_service)
):
    """
    Start a new build process.
    
    Args:
        request: Build start request with project details
        build_service: Build service instance
        
    Returns:
        Build response with build details
    """
    try:
        build = build_service.start_build(request)
        return build
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start build: {str(e)}")


@router.get("/status/{build_id}", response_model=BuildResponse)
async def get_build_status(
    build_id: int,
    build_service: BuildService = Depends(get_build_service)
):
    """
    Get build status by ID.
    
    Args:
        build_id: Build ID
        build_service: Build service instance
        
    Returns:
        Build response with status details
    """
    build = build_service.get_build_status(build_id)
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")
    return build


@router.get("/log/{build_id}")
async def get_build_log(
    build_id: int,
    build_service: BuildService = Depends(get_build_service)
):
    """
    Get build log content.
    
    Args:
        build_id: Build ID
        build_service: Build service instance
        
    Returns:
        Log content as plain text
    """
    log_content = build_service.get_build_log(build_id)
    if log_content is None:
        raise HTTPException(status_code=404, detail="Build not found")
    
    return {"build_id": build_id, "log": log_content}


@router.get("/history", response_model=BuildHistoryResponse)
async def get_build_history(
    project_id: int = Query(None, description="Filter by project ID"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    build_service: BuildService = Depends(get_build_service)
):
    """
    Get build history with optional filtering.
    
    Args:
        project_id: Filter by project ID (optional)
        limit: Maximum number of results
        offset: Offset for pagination
        build_service: Build service instance
        
    Returns:
        Build history response with builds list and total count
    """
    builds, total = build_service.get_build_history(project_id, limit, offset)
    return BuildHistoryResponse(builds=builds, total=total)
