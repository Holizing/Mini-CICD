from datetime import datetime
from typing import Literal, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from backend.deploy.artifacts import (
    validate_health_check_path,
    validate_identifier,
    validate_port_mapping,
    validate_remote_host,
    validate_remote_user,
)


BuildType = Literal["source", "docker"]
DeliveryStatus = Literal[
    "queued",
    "building",
    "build_succeeded",
    "deploying",
    "success",
    "failed",
    "ignored",
]


def normalize_optional_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def validate_absolute_linux_path(value: str, label: str) -> str:
    stripped = value.strip()
    if not stripped.startswith("/"):
        raise ValueError(f"{label} must be an absolute Linux path")
    return stripped


class DeploymentTargetUpdate(BaseModel):
    host: str = Field(min_length=1, max_length=255)
    port: int = Field(default=22, ge=1, le=65535)
    server_user: str = Field(min_length=1, max_length=255)
    private_key_path: str = Field(min_length=1, max_length=500)
    known_hosts_path: str = Field(min_length=1, max_length=500)

    @field_validator("host")
    @classmethod
    def validate_host(cls, value: str) -> str:
        return validate_remote_host(value.strip())

    @field_validator("server_user")
    @classmethod
    def validate_user(cls, value: str) -> str:
        return validate_remote_user(value.strip())

    @field_validator("private_key_path")
    @classmethod
    def validate_private_key_path(cls, value: str) -> str:
        return validate_absolute_linux_path(value, "Private key path")

    @field_validator("known_hosts_path")
    @classmethod
    def validate_known_hosts_path(cls, value: str) -> str:
        return validate_absolute_linux_path(value, "Known hosts path")


class DeploymentTargetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    configured: bool
    host: Optional[str] = None
    port: int = 22
    server_user: Optional[str] = None
    private_key_path: Optional[str] = None
    known_hosts_path: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class DeploymentTargetTestResponse(BaseModel):
    success: bool
    message: str


class ProjectAutomationUpdate(BaseModel):
    enabled: bool = False
    build_type: BuildType = "source"
    build_script: Optional[str] = Field(default=None, max_length=10000)
    docker_mode: Optional[Literal["build_from_git"]] = None
    image_name: Optional[str] = Field(default=None, max_length=255)
    image_tag: Optional[str] = Field(default="latest", max_length=50)
    dockerfile_path: Optional[str] = Field(default="./Dockerfile", max_length=500)
    build_context: Optional[str] = Field(default=".", max_length=500)
    container_name: Optional[str] = Field(default=None, max_length=255)
    port_mapping: Optional[str] = Field(default=None, max_length=100)
    health_check_port: Optional[int] = Field(default=None, ge=1, le=65535)
    health_check_path: str = Field(default="/", max_length=2048)

    @field_validator(
        "build_script",
        "docker_mode",
        "image_name",
        "image_tag",
        "dockerfile_path",
        "build_context",
        "container_name",
        "port_mapping",
    )
    @classmethod
    def strip_optional_text(cls, value: Optional[str]) -> Optional[str]:
        return normalize_optional_text(value)

    @field_validator("container_name")
    @classmethod
    def validate_container_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return validate_identifier(value, "Container name")

    @field_validator("port_mapping")
    @classmethod
    def validate_mapping(cls, value: Optional[str]) -> Optional[str]:
        return validate_port_mapping(value)

    @field_validator("health_check_path")
    @classmethod
    def validate_health_path(cls, value: str) -> str:
        return validate_health_check_path(value)

    @model_validator(mode="after")
    def validate_docker_options(self):
        if self.build_type == "source":
            self.docker_mode = None
            self.image_name = None
            self.image_tag = None
            self.dockerfile_path = None
            self.build_context = None
            self.container_name = None
            self.port_mapping = None
            return self

        self.docker_mode = "build_from_git"
        if not self.image_name:
            raise ValueError("image_name is required for Docker automation")
        if not self.container_name:
            raise ValueError("container_name is required for Docker automation")
        self.image_tag = self.image_tag or "latest"
        self.dockerfile_path = self.dockerfile_path or "./Dockerfile"
        self.build_context = self.build_context or "."
        return self


class ProjectAutomationResponse(ProjectAutomationUpdate):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    project_id: int
    configured: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class WebhookDeliveryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    delivery_id: str
    event_type: str
    repository: Optional[str]
    branch: Optional[str]
    commit_sha: Optional[str]
    project_id: Optional[int]
    build_id: Optional[int]
    deploy_id: Optional[int]
    status: DeliveryStatus
    error_message: Optional[str]
    received_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    updated_at: datetime


class WebhookDeliveryListResponse(BaseModel):
    deliveries: list[WebhookDeliveryResponse]
    total: int


class WebhookAcceptedResponse(BaseModel):
    delivery_id: str
    status: DeliveryStatus
    duplicate: bool = False
    message: str
