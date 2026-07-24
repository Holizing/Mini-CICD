from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BuildStartRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    project_id: int = Field(gt=0)
    build_type: Literal["source", "docker"] = "source"
    build_script: Optional[str] = None
    docker_mode: Optional[Literal["build_from_git", "existing_image"]] = None
    image_name: Optional[str] = None
    image_tag: Optional[str] = "latest"
    dockerfile_path: Optional[str] = "./Dockerfile"
    build_context: Optional[str] = "."
    docker_image: Optional[str] = None
    docker_compose_file: Optional[str] = None

    @model_validator(mode="after")
    def validate_build_options(self):
        if self.build_type != "docker":
            return self

        self.docker_mode = self.docker_mode or "build_from_git"
        if self.docker_mode == "existing_image" and not self.docker_image:
            raise ValueError("docker_image is required for existing_image mode")
        if self.docker_mode == "build_from_git" and not self.image_name:
            raise ValueError("image_name is required for build_from_git mode")
        return self


class BuildExecutionInput(BaseModel):
    repo_url: str
    workspace_dir: str
    logs_dir: str
    timeout_seconds: int = Field(ge=1)


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
