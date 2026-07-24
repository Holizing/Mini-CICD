from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from backend.common.database import BASE_DIR
from backend.settings.service import get_settings


@dataclass(frozen=True)
class ExecutionSettings:
    workspace_dir: str
    logs_dir: str
    default_deploy_path: str
    default_service_name: str
    build_timeout_seconds: int
    deploy_timeout_seconds: int
    docker_enabled: bool


def resolve_runtime_path(value: str) -> str:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = Path(BASE_DIR) / path
    return str(path.resolve())


def get_execution_settings(db: Session) -> ExecutionSettings:
    settings = get_settings(db)
    return ExecutionSettings(
        workspace_dir=resolve_runtime_path(settings.workspace_dir),
        logs_dir=resolve_runtime_path(settings.logs_dir),
        default_deploy_path=settings.default_deploy_path,
        default_service_name=settings.default_service_name,
        build_timeout_seconds=settings.build_timeout_seconds,
        deploy_timeout_seconds=settings.deploy_timeout_seconds,
        docker_enabled=settings.docker_enabled,
    )
