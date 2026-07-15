import os
import time
from datetime import datetime
from typing import Optional
from fastapi import BackgroundTasks
from sqlalchemy.orm import Session
from backend.build.models import Build
from backend.common.database import SessionLocal
from backend.build.schemas import BuildStartRequest, BuildResponse
from backend.build.runner import BuildRunner
from backend.build.utils import get_log_path


class BuildService:
    def __init__(self, db: Session, workspace_dir: str, logs_dir: str):
        self.db = db
        self.workspace_dir = workspace_dir
        self.logs_dir = logs_dir
        self.runner = BuildRunner(workspace_dir, logs_dir, db_session=db)

    def start_build(self, request: BuildStartRequest, background_tasks: BackgroundTasks) -> BuildResponse:
        """
        Start a new build process.
        
        Args:
            request: Build start request with project details
            background_tasks: FastAPI background tasks
            
        Returns:
            Build response with build details
        """
        # Validation based on docker_mode
        if request.build_type == "docker" and request.docker_mode == "existing_image":
            if not request.docker_image:
                raise ValueError("docker_image is required for existing_image mode")
        elif request.build_type == "docker" and request.docker_mode == "build_from_git":
            if not request.git_url or not request.branch:
                raise ValueError("git_url and branch are required for build_from_git mode")
            if not request.image_name:
                raise ValueError("image_name is required for build_from_git mode")
        elif request.build_type == "source":
            if not request.git_url or not request.branch:
                raise ValueError("git_url and branch are required for source build")
        
        request_start_time = time.time()
        # Create build record
        build = Build(
            project_id=request.project_id,
            project_name=request.project_name,
            branch=request.branch,
            build_type=request.build_type,
            build_script=request.build_script,
            docker_mode=request.docker_mode,
            image_name=request.image_name,
            image_tag=request.image_tag,
            dockerfile_path=request.dockerfile_path,
            build_context=request.build_context,
            docker_image=request.docker_image,
            docker_compose_file=request.docker_compose_file,
            status="running",
            log_path=get_log_path(self.logs_dir, 0)  # Temporary, will update after getting ID
        )
        
        self.db.add(build)
        self.db.commit()
        self.db.refresh(build)
        
        # Update log path with actual build ID
        build.log_path = get_log_path(self.logs_dir, build.id)
        self.db.commit()
        
        request_duration = time.time() - request_start_time
        
        # Log request timings
        self.runner._log(build.log_path, f"HTTP request start: {datetime.utcfromtimestamp(request_start_time).isoformat()}Z")
        self.runner._log(build.log_path, f"HTTP response sent (Request duration: {request_duration:.4f}s)")
        
        # Execute build asynchronously in background
        background_tasks.add_task(
            self._execute_build_task,
            build.id,
            request.git_url,
            request.branch,
            request.build_script,
            request.build_type,
            request.docker_mode,
            request.image_name,
            request.image_tag,
            request.dockerfile_path,
            request.build_context,
            request.docker_image,
            request.docker_compose_file
        )

        return self._build_to_response(build)

    def _execute_build_task(self, build_id: int, git_url: Optional[str], branch: Optional[str], build_script: Optional[str] = None, build_type: str = "source", docker_mode: Optional[str] = "build_from_git", image_name: Optional[str] = None, image_tag: Optional[str] = None, dockerfile_path: Optional[str] = None, build_context: Optional[str] = None, docker_image: Optional[str] = None, docker_compose_file: Optional[str] = None) -> None:
        """
        Execute build asynchronously.

        Args:
            build_id: Build database ID
            git_url: Git repository URL (optional for existing docker image mode)
            branch: Git branch (optional for existing docker image mode)
            build_script: Custom build script (optional)
            build_type: Build type (source or docker)
            docker_mode: Docker mode (build_from_git, existing_image)
            image_name: Docker image name (for docker build)
            image_tag: Docker image tag (for docker build)
            dockerfile_path: Path to Dockerfile (for docker build)
            build_context: Build context (for docker build)
            docker_image: Full docker image name with tag (for existing image mode)
            docker_compose_file: Docker Compose file (for existing image mode)
        """
        db = SessionLocal()
        try:
            build = db.query(Build).filter(Build.id == build_id).first()
            if not build:
                return

            start_time = time.time()
            self.runner._log(build.log_path, f"Build start timestamp: {datetime.utcnow().isoformat()}Z")

            success, commit_hash, error_message, artifact_path, artifact_type, detection_result = self.runner.execute_build(
                git_url=git_url,
                project_name=build.project_name,
                branch=branch,
                build_id=build.id,
                build_script=build_script,
                build_type=build_type,
                docker_mode=docker_mode,
                image_name=image_name,
                image_tag=image_tag,
                dockerfile_path=dockerfile_path,
                build_context=build_context,
                docker_image=docker_image,
                docker_compose_file=docker_compose_file
            )
            
            # Update build record
            end_time = datetime.utcnow()
            duration = int(time.time() - start_time)
            
            self.runner._log(build.log_path, f"Build finish timestamp: {end_time.isoformat()}Z")
            self.runner._log(build.log_path, f"Build duration: {duration}s")

            build.status = "success" if success else "failed"
            build.commit_hash = commit_hash
            build.artifact_path = artifact_path
            build.artifact_type = artifact_type
            build.end_time = end_time
            build.duration = duration
            
            # Save detection results if available
            if detection_result and success:
                build.detected_framework = detection_result.get('framework')
                build.detected_runtime = detection_result.get('runtime')
                build.detected_build_tool = detection_result.get('build_tool')
                build.detected_packaging = detection_result.get('packaging')
                build.recommended_deploy_script = detection_result.get('recommended_deploy_script')
                build.recommended_deploy_path = detection_result.get('recommended_deploy_path')
                build.recommended_service_name = detection_result.get('recommended_service_name')

            if not success:
                build.error_message = error_message

            db.commit()
            
        except Exception as e:
            # Handle unexpected errors
            end_time = datetime.utcnow()
            duration = int(time.time() - start_time)
            
            if build:
                build.status = "failed"
                build.end_time = end_time
                build.duration = duration
                build.error_message = f"Unexpected error: {str(e)}"
                
                db.commit()
        finally:
            db.close()

    def get_build_status(self, build_id: int) -> Optional[BuildResponse]:
        """
        Get build status by ID.
        
        Args:
            build_id: Build ID
            
        Returns:
            Build response or None if not found
        """
        build = self.db.query(Build).filter(Build.id == build_id).first()
        if not build:
            return None
        
        return self._build_to_response(build)

    def get_build_log(self, build_id: int) -> Optional[str]:
        """
        Get build log content.
        
        Args:
            build_id: Build ID
            
        Returns:
            Log content or None if not found
        """
        build = self.db.query(Build).filter(Build.id == build_id).first()
        if not build or not build.log_path:
            return None
        
        if not os.path.exists(build.log_path):
            return "Log file not found"
        
        try:
            with open(build.log_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Error reading log file: {str(e)}"

    def get_build_history(
        self,
        project_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0
    ) -> tuple[list[BuildResponse], int]:
        """
        Get build history with optional filtering.
        
        Args:
            project_id: Filter by project ID (optional)
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            Tuple of (builds list, total count)
        """
        query = self.db.query(Build)
        
        if project_id:
            query = query.filter(Build.project_id == project_id)
        
        total = query.count()
        builds = query.order_by(Build.id.desc()).offset(offset).limit(limit).all()
        
        return [self._build_to_response(build) for build in builds], total

    def _build_to_response(self, build: Build) -> BuildResponse:
        """
        Convert Build model to BuildResponse schema.

        Args:
            build: Build model instance

        Returns:
            BuildResponse schema
        """
        return BuildResponse(
            id=build.id,
            project_id=build.project_id,
            project_name=build.project_name,
            branch=build.branch,
            commit_hash=build.commit_hash,
            build_type=build.build_type,
            build_script=build.build_script,
            docker_mode=build.docker_mode,
            image_name=build.image_name,
            image_tag=build.image_tag,
            dockerfile_path=build.dockerfile_path,
            build_context=build.build_context,
            docker_image=build.docker_image,
            docker_compose_file=build.docker_compose_file,
            artifact_path=build.artifact_path,
            artifact_type=build.artifact_type,
            detected_framework=build.detected_framework,
            detected_runtime=build.detected_runtime,
            detected_build_tool=build.detected_build_tool,
            detected_packaging=build.detected_packaging,
            recommended_deploy_script=build.recommended_deploy_script,
            recommended_deploy_path=build.recommended_deploy_path,
            recommended_service_name=build.recommended_service_name,
            status=build.status,
            start_time=build.start_time,
            end_time=build.end_time,
            duration=build.duration,
            log_path=build.log_path,
            error_message=build.error_message
        )

    def get_build_stages(self, build_id: int):
        """
        Get all stages for a build.

        Args:
            build_id: Build ID

        Returns:
            List of BuildStageResponse schemas or None if build not found
        """
        from backend.build.models import BuildStage
        from backend.build.schemas import BuildStageResponse

        # Check if build exists
        build = self.db.query(Build).filter(Build.id == build_id).first()
        if not build:
            return None

        # Get all stages for this build
        stages = self.db.query(BuildStage).filter(BuildStage.build_id == build_id).order_by(BuildStage.id).all()

        return [BuildStageResponse(
            id=stage.id,
            build_id=stage.build_id,
            stage_name=stage.stage_name,
            status=stage.status,
            started_at=stage.started_at,
            finished_at=stage.finished_at,
            duration=stage.duration,
            log_file=stage.log_file,
            error_message=stage.error_message
        ) for stage in stages]

    def get_stage_log(self, build_id: int, stage_name: str):
        """
        Get log content for a specific stage.

        Args:
            build_id: Build ID
            stage_name: Stage name

        Returns:
            Log content as string or None if not found
        """
        from backend.build.models import BuildStage

        # Find the stage
        stage = self.db.query(BuildStage).filter(
            BuildStage.build_id == build_id,
            BuildStage.stage_name == stage_name
        ).first()

        if not stage or not stage.log_file:
            return None

        # Read the log file
        try:
            with open(stage.log_file, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return None
