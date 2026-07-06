from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


ProjectStatus = Literal["active", "inactive"]


def normalize_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return value
    stripped = value.strip()
    return stripped or None


def is_supported_repo_url(value: str) -> bool:
    return (
        value.startswith("https://")
        or value.startswith("http://")
        or value.startswith("git@")
        or value.startswith("ssh://")
    )


class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    repo_url: str = Field(..., min_length=1, max_length=500)
    branch: str = Field(default="main", min_length=1, max_length=255)
    description: Optional[str] = None
    deploy_path: str = Field(..., min_length=1, max_length=500)
    service_name: str = Field(..., min_length=1, max_length=255)
    status: ProjectStatus = "active"

    @field_validator("name", "repo_url", "branch", "deploy_path", "service_name")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field cannot be empty")
        return stripped

    @field_validator("description")
    @classmethod
    def strip_description(cls, value: Optional[str]) -> Optional[str]:
        return normalize_text(value)

    @field_validator("repo_url")
    @classmethod
    def validate_repo_url(cls, value: str) -> str:
        if not is_supported_repo_url(value):
            raise ValueError("Repository URL must start with http://, https://, ssh://, or git@")
        return value

    @field_validator("deploy_path")
    @classmethod
    def validate_deploy_path(cls, value: str) -> str:
        if not value.startswith("/"):
            raise ValueError("Deploy path must be an absolute Linux path")
        return value


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    repo_url: Optional[str] = Field(default=None, min_length=1, max_length=500)
    branch: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    deploy_path: Optional[str] = Field(default=None, min_length=1, max_length=500)
    service_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    status: Optional[ProjectStatus] = None

    @field_validator("name", "repo_url", "branch", "deploy_path", "service_name")
    @classmethod
    def strip_optional_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field cannot be empty")
        return stripped

    @field_validator("description")
    @classmethod
    def strip_description(cls, value: Optional[str]) -> Optional[str]:
        return normalize_text(value)

    @field_validator("repo_url")
    @classmethod
    def validate_repo_url(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not is_supported_repo_url(value):
            raise ValueError("Repository URL must start with http://, https://, ssh://, or git@")
        return value

    @field_validator("deploy_path")
    @classmethod
    def validate_deploy_path(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not value.startswith("/"):
            raise ValueError("Deploy path must be an absolute Linux path")
        return value


class ProjectResponse(ProjectBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class ProjectListResponse(BaseModel):
    projects: list[ProjectResponse]
    total: int
