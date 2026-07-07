from sqlalchemy.orm import Session

from backend.settings.models import SystemSettings
from backend.settings.schemas import SettingsUpdate


DEFAULT_SETTINGS = {
    "workspace_dir": "workspace",
    "logs_dir": "logs",
    "default_branch": "main",
    "default_deploy_path": "/var/www/mini-cicd",
    "default_service_name": "mini-cicd-app",
    "build_timeout_seconds": 600,
    "deploy_timeout_seconds": 600,
    "auto_deploy_enabled": False,
    "docker_enabled": True,
    "webhook_secret": None,
}


def get_settings(db: Session) -> SystemSettings:
    settings = db.query(SystemSettings).order_by(SystemSettings.id.asc()).first()
    if settings is None:
        settings = SystemSettings(**DEFAULT_SETTINGS)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


def update_settings(db: Session, settings_data: SettingsUpdate) -> SystemSettings:
    settings = get_settings(db)
    update_data = settings_data.model_dump(exclude_unset=True)
    webhook_secret = update_data.pop("webhook_secret", None)

    for field, value in update_data.items():
        setattr(settings, field, value)

    if webhook_secret:
        settings.webhook_secret = webhook_secret

    db.commit()
    db.refresh(settings)
    return settings


def reset_settings(db: Session) -> SystemSettings:
    settings = get_settings(db)

    for field, value in DEFAULT_SETTINGS.items():
        setattr(settings, field, value)

    db.commit()
    db.refresh(settings)
    return settings
