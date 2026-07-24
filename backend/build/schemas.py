from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class BuildStartRequest(BaseModel):
    project_id: int
    project_name: str
    branch: Optional[str] = None  # Optional for existing docker image mode
    git_url: Optional[str] = None  # Optional for existing docker image mode
    build_type: str = Field(default="source")  # source, docker
    build_script: Optional[str] = None
    # Docker-specific build fields
    docker_mode: Optional[str] = Field(default="build_from_git")  # build_from_git, existing_image
    image_name: Optional[str] = None  # Required for docker build
    image_tag: Optional[str] = "latest"
    dockerfile_path: Optional[str] = "./Dockerfile"
    build_context: Optional[str] = "."
    # Existing docker image mode fields
    docker_image: Optional[str] = None  # Full image name with tag (e.g., nginx:latest)
    docker_compose_file: Optional[str] = None  # Docker Compose file for existing image


class BuildResponse(BaseModel):
    id: int
    project_id: int
    project_name: str
    branch: Optional[str]
    commit_hash: Optional[str]
    build_type: str
    build_script: Optional[str]
    # Docker-specific build fields
    docker_mode: Optional[str] = None  # build_from_git, existing_image
    image_name: Optional[str] = None
    image_tag: Optional[str] = None
    dockerfile_path: Optional[str] = None
    build_context: Optional[str] = None
    # Existing docker image mode fields
    docker_image: Optional[str] = None
    docker_compose_file: Optional[str] = None
    artifact_path: Optional[str]
    artifact_type: Optional[str]
    # Detection fields for deployment recommendations
    detected_framework: Optional[str] = None
    detected_runtime: Optional[str] = None
    detected_build_tool: Optional[str] = None
    detected_packaging: Optional[str] = None
    recommended_deploy_script: Optional[str] = None
    recommended_deploy_path: Optional[str] = None
    recommended_service_name: Optional[str] = None
    status: str
    start_time: datetime
    end_time: Optional[datetime]
    duration: Optional[int]
    log_path: Optional[str]
    error_message: Optional[str]

    class Config:
        from_attributes = True


class BuildStageResponse(BaseModel):
    id: int
    build_id: int
    stage_name: str
    status: str  # pending, running, success, failed
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    duration: Optional[int]
    log_file: Optional[str]
    error_message: Optional[str]

    class Config:
        from_attributes = True


class BuildStatusResponse(BaseModel):
    build_id: int
    status: str
    progress: str


class BuildHistoryResponse(BaseModel):
    builds: list[BuildResponse]
    total: int
