from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from backend.common.database import get_db
from backend.common.runtime import get_execution_settings
from backend.build.schemas import BuildStartRequest, BuildResponse, BuildHistoryResponse, BuildStageResponse
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
    settings = get_execution_settings(db)
    return BuildService(
        db=db,
        workspace_dir=settings.workspace_dir,
        logs_dir=settings.logs_dir,
        timeout_seconds=settings.build_timeout_seconds,
        docker_enabled=settings.docker_enabled,
    )


@router.post("/start", response_model=BuildResponse)
async def start_build(
    request: BuildStartRequest,
    background_tasks: BackgroundTasks,
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
        build = build_service.start_build(request, background_tasks)
        return build
    except HTTPException:
        raise
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))
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


@router.get("/stages/{build_id}", response_model=list[BuildStageResponse])
async def get_build_stages(
    build_id: int,
    build_service: BuildService = Depends(get_build_service)
):
    """
    Get all stages for a build.

    Args:
        build_id: Build ID
        build_service: Build service instance

    Returns:
        List of build stages with their status and timing
    """
    stages = build_service.get_build_stages(build_id)
    if stages is None:
        raise HTTPException(status_code=404, detail="Build not found")
    return stages


@router.get("/stage/{build_id}/{stage_name}")
async def get_stage_log(
    build_id: int,
    stage_name: str,
    build_service: BuildService = Depends(get_build_service)
):
    """
    Get log content for a specific stage.

    Args:
        build_id: Build ID
        stage_name: Stage name (e.g., "Clone Repository")
        build_service: Build service instance

    Returns:
        Stage log content as plain text
    """
    log_content = build_service.get_stage_log(build_id, stage_name)
    if log_content is None:
        raise HTTPException(status_code=404, detail="Stage or build not found")

    return {"build_id": build_id, "stage_name": stage_name, "log": log_content}
