from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from backend.common.database import Base


class Build(Base):
    __tablename__ = "builds"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    project_id = Column(Integer, nullable=False, index=True)
    project_name = Column(String(255), nullable=False)
    branch = Column(String(255), nullable=True)  # Nullable for existing docker image mode
    commit_hash = Column(String(255), nullable=True)
    build_type = Column(String(50), nullable=False, default="source")  # source, docker
    build_script = Column(Text, nullable=True)  # Custom build script
    # Docker-specific build fields
    docker_mode = Column(String(50), nullable=True, default="build_from_git")  # build_from_git, existing_image
    image_name = Column(String(255), nullable=True)
    image_tag = Column(String(50), nullable=True)
    dockerfile_path = Column(String(500), nullable=True)
    build_context = Column(String(500), nullable=True)
    # Existing docker image mode fields
    docker_image = Column(String(500), nullable=True)  # Full image name with tag (e.g., nginx:latest)
    docker_compose_file = Column(String(500), nullable=True)  # Docker Compose file for existing image
    artifact_path = Column(Text, nullable=True)  # Path to built artifact (.war, .jar, .zip, etc.)
    artifact_type = Column(String(50), nullable=True)  # file, directory, docker_image
    # Detection fields for deployment recommendations
    detected_framework = Column(String(255), nullable=True)  # Spring Boot, Express, Django, etc.
    detected_runtime = Column(String(50), nullable=True)  # Java, Node.js, Python, etc.
    detected_build_tool = Column(String(50), nullable=True)  # Maven, Gradle, npm, pip, etc.
    detected_packaging = Column(String(50), nullable=True)  # JAR, WAR, zip, etc.
    recommended_deploy_script = Column(Text, nullable=True)  # Recommended deploy script
    recommended_deploy_path = Column(String(500), nullable=True)  # Recommended deploy path
    recommended_service_name = Column(String(255), nullable=True)  # Recommended service name
    status = Column(String(50), nullable=False, default="running")  # running, success, failed
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration = Column(Integer, nullable=True)  # in seconds
    log_path = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    # Relationship to build stages
    stages = relationship("BuildStage", back_populates="build", cascade="all, delete-orphan")


class BuildStage(Base):
    __tablename__ = "build_stages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    build_id = Column(Integer, ForeignKey("builds.id"), nullable=False, index=True)
    stage_name = Column(String(255), nullable=False)  # Clone Repository, Execute Build Script, etc.
    status = Column(String(50), nullable=False, default="pending")  # pending, running, success, failed
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    duration = Column(Integer, nullable=True)  # in seconds
    log_file = Column(Text, nullable=True)  # Path to stage-specific log file
    error_message = Column(Text, nullable=True)

    # Relationship to build
    build = relationship("Build", back_populates="stages")
