from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from backend.common.database import get_db
from backend.common.runtime import get_execution_settings
from backend.deploy.schemas import (
    DeployHistoryResponse,
    DeploymentCapabilityResponse,
    DeployResponse,
    DeployStageResponse,
    DeployStartRequest,
)
from backend.deploy.service import DeployService
from backend.deploy.strategies import get_registry


router = APIRouter(prefix="/deploy", tags=["deploy"])


def get_deploy_service(
    db: Session = Depends(get_db)
) -> DeployService:
    """
    Dependency to get DeployService instance.
    
    Args:
        db: Database session
        
    Returns:
        DeployService instance
    """
    settings = get_execution_settings(db)
    return DeployService(
        db=db,
        logs_dir=settings.logs_dir,
        workspace_dir=settings.workspace_dir,
        timeout_seconds=settings.deploy_timeout_seconds,
        docker_enabled=settings.docker_enabled,
        default_deploy_path=settings.default_deploy_path,
        default_service_name=settings.default_service_name,
    )


@router.post("/start", response_model=DeployResponse)
async def start_deploy(
    request: DeployStartRequest,
    background_tasks: BackgroundTasks,
    deploy_service: DeployService = Depends(get_deploy_service)
):
    """
    Start a new deploy process.
    
    Args:
        request: Deploy start request with deploy details
        deploy_service: Deploy service instance
        
    Returns:
        Deploy response with deploy details
    """
    try:
        deploy = deploy_service.start_deploy(request, background_tasks)
        return deploy
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start deploy: {str(e)}")


@router.get(
    "/capabilities",
    response_model=list[DeploymentCapabilityResponse],
)
async def get_deployment_capabilities():
    """Return the deploy profiles enabled by the current server."""
    return get_registry().list_capabilities()


@router.get("/status/{deploy_id}", response_model=DeployResponse)
async def get_deploy_status(
    deploy_id: int,
    deploy_service: DeployService = Depends(get_deploy_service)
):
    """
    Get deploy status by ID.
    
    Args:
        deploy_id: Deploy ID
        deploy_service: Deploy service instance
        
    Returns:
        Deploy response with status details
    """
    deploy = deploy_service.get_deploy_status(deploy_id)
    if not deploy:
        raise HTTPException(status_code=404, detail="Deploy not found")
    return deploy


@router.get("/log/{deploy_id}")
async def get_deploy_log(
    deploy_id: int,
    deploy_service: DeployService = Depends(get_deploy_service)
):
    """
    Get deploy log content.
    
    Args:
        deploy_id: Deploy ID
        deploy_service: Deploy service instance
        
    Returns:
        Log content as plain text
    """
    log_content = deploy_service.get_deploy_log(deploy_id)
    if log_content is None:
        raise HTTPException(status_code=404, detail="Deploy not found")
    
    return {"deploy_id": deploy_id, "log": log_content}


@router.get("/history", response_model=DeployHistoryResponse)
async def get_deploy_history(
    project_id: int = Query(None, description="Filter by project ID"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    deploy_service: DeployService = Depends(get_deploy_service)
):
    """
    Get deploy history with optional filtering.

    Args:
        project_id: Filter by project ID (optional)
        limit: Maximum number of results
        offset: Offset for pagination
        deploy_service: Deploy service instance

    Returns:
        Deploy history response with deploys list and total count
    """
    deploys, total = deploy_service.get_deploy_history(project_id, limit, offset)
    return DeployHistoryResponse(deploys=deploys, total=total)


@router.get("/stages/{deploy_id}", response_model=list[DeployStageResponse])
async def get_deploy_stages(
    deploy_id: int,
    deploy_service: DeployService = Depends(get_deploy_service)
):
    """
    Get all stages for a deploy.

    Args:
        deploy_id: Deploy ID
        deploy_service: Deploy service instance

    Returns:
        List of deploy stages with their status and timing
    """
    stages = deploy_service.get_deploy_stages(deploy_id)
    if stages is None:
        raise HTTPException(status_code=404, detail="Deploy not found")
    return stages


@router.get("/stage/{deploy_id}/{stage_name}")
async def get_stage_log(
    deploy_id: int,
    stage_name: str,
    deploy_service: DeployService = Depends(get_deploy_service)
):
    """
    Get log content for a specific stage.

    Args:
        deploy_id: Deploy ID
        stage_name: Stage name (e.g., "Upload Artifact")
        deploy_service: Deploy service instance

    Returns:
        Stage log content as plain text
    """
    log_content = deploy_service.get_stage_log(deploy_id, stage_name)
    if log_content is None:
        raise HTTPException(status_code=404, detail="Stage or deploy not found")

    return {"deploy_id": deploy_id, "stage_name": stage_name, "log": log_content}
