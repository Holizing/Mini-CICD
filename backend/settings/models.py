from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from backend.common.database import Base


class SystemSettings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    workspace_dir = Column(String(500), nullable=False, default="workspace")
    logs_dir = Column(String(500), nullable=False, default="logs")
    default_branch = Column(String(255), nullable=False, default="main")
    default_deploy_path = Column(String(500), nullable=False, default="/var/www/mini-cicd")
    default_service_name = Column(String(255), nullable=False, default="mini-cicd-app")
    build_timeout_seconds = Column(Integer, nullable=False, default=600)
    deploy_timeout_seconds = Column(Integer, nullable=False, default=600)
    auto_deploy_enabled = Column(Boolean, nullable=False, default=False)
    docker_enabled = Column(Boolean, nullable=False, default=True)
    webhook_secret = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    @property
    def webhook_secret_configured(self) -> bool:
        return bool(self.webhook_secret)
