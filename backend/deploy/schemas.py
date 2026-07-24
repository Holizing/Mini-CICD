from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class DeployStartRequest(BaseModel):
    build_id: int
    project_id: int
    project_name: str
    branch: Optional[str] = None  # Optional for existing docker image mode
    server_ip: str
    server_user: str = Field(default="root")
    server_password: Optional[str] = None
    server_ssh_key: Optional[str] = None
    deploy_path: Optional[str] = None  # Required for source deploy
    service_name: Optional[str] = None  # Required for source deploy
    deploy_type: str = Field(default="source")  # source, docker
    deploy_script: Optional[str] = None
    # Docker-specific fields
    docker_mode: Optional[str] = Field(default="build_from_git")  # build_from_git, existing_image
    container_name: Optional[str] = None  # Required for docker deploy
    image_name: Optional[str] = None  # Required for docker deploy
    image_tag: Optional[str] = "latest"  # Default to latest
    port_mapping: Optional[str] = None  # e.g. "8080:80" for docker deploy
    # Existing docker image mode fields
    docker_image: Optional[str] = None  # Full image name with tag (e.g., nginx:latest)
    docker_compose_file: Optional[str] = None  # Docker Compose file for existing image


class DeployResponse(BaseModel):
    id: int
    build_id: int
    project_id: int
    project_name: str
    branch: Optional[str]
    server_ip: str
    server_user: str
    deploy_path: Optional[str]
    service_name: Optional[str]
    deploy_type: str
    deploy_script: Optional[str] = None
    # Docker-specific fields
    docker_mode: Optional[str] = None  # build_from_git, existing_image
    container_name: Optional[str] = None
    image_name: Optional[str] = None
    image_tag: Optional[str] = None
    port_mapping: Optional[str] = None
    # Existing docker image mode fields
    docker_image: Optional[str] = None
    docker_compose_file: Optional[str] = None
    status: str
    start_time: datetime
    end_time: Optional[datetime]
    duration: Optional[int]
    log_path: Optional[str]
    error_message: Optional[str]

    class Config:
        from_attributes = True


class DeployStageResponse(BaseModel):
    id: int
    deploy_id: int
    stage_name: str
    status: str  # pending, running, success, failed
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    duration: Optional[int]
    log_file: Optional[str]
    error_message: Optional[str]

    class Config:
        from_attributes = True


class DeployHistoryResponse(BaseModel):
    deploys: list[DeployResponse]
    total: int
