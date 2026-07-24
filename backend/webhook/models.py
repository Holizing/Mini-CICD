from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.sql import func

from backend.common.database import Base


class DeploymentTargetSettings(Base):
    __tablename__ = "deployment_target_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False, default=22)
    server_user = Column(String(255), nullable=False)
    private_key_path = Column(String(500), nullable=False)
    known_hosts_path = Column(String(500), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class ProjectAutomationConfig(Base):
    __tablename__ = "project_automation_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    enabled = Column(Boolean, nullable=False, default=False)
    build_type = Column(String(50), nullable=False, default="source")
    build_script = Column(Text, nullable=True)
    docker_mode = Column(String(50), nullable=True)
    image_name = Column(String(255), nullable=True)
    image_tag = Column(String(50), nullable=True)
    dockerfile_path = Column(String(500), nullable=True)
    build_context = Column(String(500), nullable=True)
    container_name = Column(String(255), nullable=True)
    port_mapping = Column(String(100), nullable=True)
    health_check_port = Column(Integer, nullable=True)
    health_check_path = Column(String(2048), nullable=False, default="/")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    delivery_id = Column(String(255), nullable=False, unique=True, index=True)
    event_type = Column(String(100), nullable=False)
    repository = Column(String(500), nullable=True, index=True)
    branch = Column(String(255), nullable=True, index=True)
    commit_sha = Column(String(64), nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    build_id = Column(Integer, ForeignKey("builds.id"), nullable=True, index=True)
    deploy_id = Column(Integer, ForeignKey("deploys.id"), nullable=True, index=True)
    status = Column(String(50), nullable=False, default="queued", index=True)
    error_message = Column(Text, nullable=True)
    received_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
