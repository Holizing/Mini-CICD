from datetime import datetime
from typing import Literal, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class DeployStartRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    build_id: int = Field(gt=0)
    server_ip: str = Field(min_length=1, max_length=255)
    server_user: str = Field(default="root", min_length=1, max_length=255)
    server_password: Optional[str] = None
    server_ssh_key: Optional[str] = None
    deploy_path: Optional[str] = Field(default=None, max_length=500)
    service_name: Optional[str] = Field(default=None, max_length=255)
    deploy_script: Optional[str] = None
    container_name: Optional[str] = Field(default=None, max_length=255)
    port_mapping: Optional[str] = Field(default=None, max_length=100)
    health_check_port: Optional[int] = Field(default=None, ge=1, le=65535)
    health_check_path: Optional[str] = Field(default="/", max_length=2048)

    @field_validator(
        "server_ip",
        "server_user",
        "server_password",
        "server_ssh_key",
        "deploy_path",
        "service_name",
        "deploy_script",
        "container_name",
        "port_mapping",
        "health_check_path",
    )
    @classmethod
    def normalize_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("deploy_path")
    @classmethod
    def validate_deploy_path(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not value.startswith("/"):
            raise ValueError("deploy_path must be an absolute Linux path")
        return value

    @field_validator("health_check_path")
    @classmethod
    def validate_health_check_path(cls, value: Optional[str]) -> str:
        path = value or "/"
        if not path.startswith("/"):
            raise ValueError("health_check_path must start with /")
        return path

    @model_validator(mode="after")
    def validate_authentication(self):
        if not self.server_password and not self.server_ssh_key:
            raise ValueError("server_password or server_ssh_key is required")
        return self


class DeployExecutionInput(BaseModel):
    build_id: int
    server_ip: str
    server_user: str
    server_password: Optional[str] = None
    server_ssh_key: Optional[str] = None
    deploy_path: Optional[str] = None
    service_name: Optional[str] = None
    deploy_type: Literal["source", "docker"]
    deploy_script: Optional[str] = None
    docker_mode: Optional[Literal["build_from_git", "existing_image"]] = None
    container_name: Optional[str] = None
    image_name: Optional[str] = None
    image_tag: Optional[str] = None
    port_mapping: Optional[str] = None
    docker_image: Optional[str] = None
    docker_compose_file: Optional[str] = None
    health_check_port: Optional[int] = Field(default=None, ge=1, le=65535)
    health_check_path: str = "/"
    workspace_dir: str
    logs_dir: str
    timeout_seconds: int = Field(ge=1)


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


class DeploymentCapabilityResponse(BaseModel):
    id: str
    name: str
    tier: Literal["verified", "experimental"]
    status: Literal[
        "verified",
        "experimental_enabled",
        "experimental_disabled",
    ]
    enabled: bool
    frameworks: list[str]
    runtimes: list[str]
    artifact_types: list[str]
    required_tools: list[str]
    default_health_check_port: Optional[int] = None
