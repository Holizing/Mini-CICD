from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from backend.common.database import Base


class Deploy(Base):
    __tablename__ = "deploys"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    build_id = Column(Integer, nullable=False, index=True)
    project_id = Column(Integer, nullable=False, index=True)
    project_name = Column(String(255), nullable=False)
    branch = Column(String(255), nullable=True)  # Nullable for existing docker image mode
    server_ip = Column(String(255), nullable=False)
    server_user = Column(String(255), nullable=False)
    deploy_path = Column(String(500), nullable=True)  # Optional for docker deploy
    service_name = Column(String(255), nullable=True)  # Optional for docker deploy
    deploy_type = Column(String(50), nullable=False, default="source")  # source, docker
    deploy_script = Column(Text, nullable=True)  # Custom deploy script
    # Docker-specific fields
    docker_mode = Column(String(50), nullable=True, default="build_from_git")  # build_from_git, existing_image
    container_name = Column(String(255), nullable=True)
    image_name = Column(String(255), nullable=True)
    image_tag = Column(String(50), nullable=True)
    port_mapping = Column(String(100), nullable=True)  # e.g. "8080:80"
    # Existing docker image mode fields
    docker_image = Column(String(500), nullable=True)  # Full image name with tag (e.g., nginx:latest)
    docker_compose_file = Column(String(500), nullable=True)  # Docker Compose file for existing image
    status = Column(String(50), nullable=False, default="running")  # running, success, failed
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration = Column(Integer, nullable=True)  # in seconds
    log_path = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    # Relationship to deploy stages
    stages = relationship("DeployStage", back_populates="deploy", cascade="all, delete-orphan")


class DeployStage(Base):
    __tablename__ = "deploy_stages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    deploy_id = Column(Integer, ForeignKey("deploys.id"), nullable=False, index=True)
    stage_name = Column(String(255), nullable=False)  # Upload Artifact, Execute Deploy Script, etc.
    status = Column(String(50), nullable=False, default="pending")  # pending, running, success, failed
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    duration = Column(Integer, nullable=True)  # in seconds
    log_file = Column(Text, nullable=True)  # Path to stage-specific log file
    error_message = Column(Text, nullable=True)

    # Relationship to deploy
    deploy = relationship("Deploy", back_populates="stages")
