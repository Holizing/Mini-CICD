from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


def normalize_optional_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return value
    stripped = value.strip()
    return stripped or None


def normalize_required_text(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError("Field cannot be empty")
    return stripped


class SettingsBase(BaseModel):
    workspace_dir: str = Field(default="workspace", min_length=1, max_length=500)
    logs_dir: str = Field(default="logs", min_length=1, max_length=500)
    default_branch: str = Field(default="main", min_length=1, max_length=255)
    default_deploy_path: str = Field(default="/var/www/mini-cicd", min_length=1, max_length=500)
    default_service_name: str = Field(default="mini-cicd-app", min_length=1, max_length=255)
    build_timeout_seconds: int = Field(default=600, ge=30, le=3600)
    deploy_timeout_seconds: int = Field(default=600, ge=30, le=3600)
    auto_deploy_enabled: bool = False
    docker_enabled: bool = True

    @field_validator(
        "workspace_dir",
        "logs_dir",
        "default_branch",
        "default_deploy_path",
        "default_service_name",
    )
    @classmethod
    def strip_required_fields(cls, value: str) -> str:
        return normalize_required_text(value)

    @field_validator("default_deploy_path")
    @classmethod
    def validate_deploy_path(cls, value: str) -> str:
        if not value.startswith("/"):
            raise ValueError("Default deploy path must be an absolute Linux path")
        return value


class SettingsUpdate(BaseModel):
    workspace_dir: Optional[str] = Field(default=None, min_length=1, max_length=500)
    logs_dir: Optional[str] = Field(default=None, min_length=1, max_length=500)
    default_branch: Optional[str] = Field(default=None, min_length=1, max_length=255)
    default_deploy_path: Optional[str] = Field(default=None, min_length=1, max_length=500)
    default_service_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    build_timeout_seconds: Optional[int] = Field(default=None, ge=30, le=3600)
    deploy_timeout_seconds: Optional[int] = Field(default=None, ge=30, le=3600)
    auto_deploy_enabled: Optional[bool] = None
    docker_enabled: Optional[bool] = None
    webhook_secret: Optional[str] = Field(default=None, max_length=255)

    @field_validator(
        "workspace_dir",
        "logs_dir",
        "default_branch",
        "default_deploy_path",
        "default_service_name",
    )
    @classmethod
    def strip_optional_required_fields(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        return normalize_required_text(value)

    @field_validator("default_deploy_path")
    @classmethod
    def validate_optional_deploy_path(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not value.startswith("/"):
            raise ValueError("Default deploy path must be an absolute Linux path")
        return value

    @field_validator("webhook_secret")
    @classmethod
    def strip_optional_webhook_secret(cls, value: Optional[str]) -> Optional[str]:
        return normalize_optional_text(value)


class SettingsResponse(SettingsBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    webhook_secret_configured: bool
    created_at: datetime
    updated_at: datetime
