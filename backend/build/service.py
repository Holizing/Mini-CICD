import os
import time
import traceback
from datetime import datetime
from typing import Optional

from fastapi import BackgroundTasks, HTTPException
from sqlalchemy.orm import Session

from backend.build.models import Build, BuildStage
from backend.build.runner import BuildRunner
from backend.build.schemas import (
    BuildExecutionInput,
    BuildResponse,
    BuildStartRequest,
)
from backend.build.utils import get_log_path
from backend.common.database import SessionLocal
from backend.deploy.artifacts import validate_project_name
from backend.project.models import Project


def run_build_worker(build_id: int, execution_data: dict) -> None:
    """Run a build with a database session owned by the background worker."""
    worker_started_at = time.time()

    try:
        execution = BuildExecutionInput.model_validate(execution_data)
        with SessionLocal() as db:
            service = BuildService(
                db=db,
                workspace_dir=execution.workspace_dir,
                logs_dir=execution.logs_dir,
                timeout_seconds=execution.timeout_seconds,
            )
            service._execute_build_task(
                build_id,
                execution.repo_url,
                execution.commit_sha,
            )
    except Exception as error:
        worker_traceback = traceback.format_exc()
        with SessionLocal() as db:
            service = BuildService(
                db=db,
                workspace_dir=execution_data["workspace_dir"],
                logs_dir=execution_data["logs_dir"],
                timeout_seconds=execution_data["timeout_seconds"],
            )
            service._mark_build_failed(
                build_id=build_id,
                error=error,
                worker_started_at=worker_started_at,
                worker_traceback=worker_traceback,
            )


class BuildService:
    def __init__(
        self,
        db: Session,
        workspace_dir: str,
        logs_dir: str,
        timeout_seconds: int = 600,
        docker_enabled: bool = True,
    ):
        self.db = db
        self.workspace_dir = os.path.abspath(workspace_dir)
        self.logs_dir = os.path.abspath(logs_dir)
        self.timeout_seconds = timeout_seconds
        self.docker_enabled = docker_enabled

    def start_build(
        self,
        request: BuildStartRequest,
        background_tasks: BackgroundTasks,
    ) -> BuildResponse:
        """Create a manual build and schedule its worker."""
        response, execution = self.prepare_build(request)
        background_tasks.add_task(
            run_build_worker,
            response.id,
            execution.model_dump(),
        )
        return response

    def prepare_build(
        self,
        request: BuildStartRequest,
        *,
        commit_sha: Optional[str] = None,
        request_source: str = "HTTP request",
    ) -> tuple[BuildResponse, BuildExecutionInput]:
        """Persist a build and return immutable data for its worker."""
        project = self.db.get(Project, request.project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        if project.status != "active":
            raise HTTPException(
                status_code=409,
                detail="Inactive projects cannot start new builds",
            )
        validate_project_name(project.name)
        if request.build_type == "docker" and not self.docker_enabled:
            raise HTTPException(
                status_code=409,
                detail="Docker execution is disabled in Settings",
            )

        request_start_time = time.time()
        build = Build(
            project_id=project.id,
            project_name=project.name,
            branch=project.branch,
            build_type=request.build_type,
            build_script=request.build_script,
            docker_mode=request.docker_mode if request.build_type == "docker" else None,
            image_name=request.image_name if request.build_type == "docker" else None,
            image_tag=request.image_tag if request.build_type == "docker" else None,
            dockerfile_path=request.dockerfile_path if request.build_type == "docker" else None,
            build_context=request.build_context if request.build_type == "docker" else None,
            docker_image=request.docker_image if request.build_type == "docker" else None,
            docker_compose_file=(
                request.docker_compose_file
                if request.build_type == "docker"
                else None
            ),
            status="running",
            log_path=get_log_path(self.logs_dir, 0),
        )

        self.db.add(build)
        self.db.commit()
        self.db.refresh(build)

        build.log_path = get_log_path(self.logs_dir, build.id)
        self.db.commit()

        request_runner = BuildRunner(
            workspace_dir=self.workspace_dir,
            logs_dir=self.logs_dir,
            db_session=self.db,
            timeout_seconds=self.timeout_seconds,
        )
        request_runner._initialize_stages(
            build.id,
            build.build_type,
            build.docker_mode,
        )

        request_duration = time.time() - request_start_time
        request_runner._log(
            build.log_path,
            (
                f"{request_source} start: "
                f"{datetime.utcfromtimestamp(request_start_time).isoformat()}Z"
            ),
        )
        request_runner._log(
            build.log_path,
            f"Build queued (Preparation duration: {request_duration:.4f}s)",
        )

        execution = BuildExecutionInput(
            repo_url=project.repo_url,
            commit_sha=commit_sha,
            workspace_dir=self.workspace_dir,
            logs_dir=self.logs_dir,
            timeout_seconds=self.timeout_seconds,
        )
        return self._build_to_response(build), execution

    def _execute_build_task(
        self,
        build_id: int,
        repo_url: str,
        commit_sha: Optional[str] = None,
    ) -> None:
        """Execute a build using this worker's database session."""
        build = self.db.get(Build, build_id)
        if build is None:
            raise ValueError(f"Build {build_id} not found")

        start_time = time.time()
        deadline = time.monotonic() + self.timeout_seconds
        runner = BuildRunner(
            workspace_dir=self.workspace_dir,
            logs_dir=self.logs_dir,
            db_session=self.db,
            timeout_seconds=self.timeout_seconds,
            deadline=deadline,
        )

        try:
            runner._log(
                build.log_path,
                f"Build start timestamp: {datetime.utcnow().isoformat()}Z",
            )
            (
                success,
                commit_hash,
                error_message,
                artifact_path,
                artifact_type,
                detection_result,
            ) = runner.execute_build(
                git_url=repo_url,
                project_name=build.project_name,
                branch=build.branch,
                build_id=build.id,
                build_script=build.build_script,
                build_type=build.build_type,
                docker_mode=build.docker_mode,
                image_name=build.image_name,
                image_tag=build.image_tag,
                dockerfile_path=build.dockerfile_path,
                build_context=build.build_context,
                docker_image=build.docker_image,
                docker_compose_file=build.docker_compose_file,
                commit_sha=commit_sha,
            )

            end_time = datetime.utcnow()
            duration = int(time.time() - start_time)

            runner._log(
                build.log_path,
                f"Build finish timestamp: {end_time.isoformat()}Z",
            )
            runner._log(build.log_path, f"Build duration: {duration}s")

            build.status = "success" if success else "failed"
            build.commit_hash = commit_hash
            build.artifact_path = artifact_path
            build.artifact_type = artifact_type
            build.end_time = end_time
            build.duration = duration
            
            if detection_result and success:
                build.detected_framework = detection_result.get('framework')
                build.detected_runtime = detection_result.get('runtime')
                build.detected_build_tool = detection_result.get('build_tool')
                build.detected_packaging = detection_result.get('packaging')
                build.recommended_deploy_script = detection_result.get('recommended_deploy_script')
                build.recommended_deploy_path = detection_result.get('recommended_deploy_path')
                build.recommended_service_name = detection_result.get('recommended_service_name')

            if not success:
                build.error_message = error_message or "Build failed"
                pending_stages = (
                    self.db.query(BuildStage)
                    .filter(
                        BuildStage.build_id == build_id,
                        BuildStage.status == "pending",
                    )
                    .all()
                )
                for stage in pending_stages:
                    stage.status = "failed"
                    stage.finished_at = end_time
                    stage.duration = 0
                    stage.error_message = (
                        error_message
                        or "Build stopped before this stage"
                    )
            else:
                build.error_message = None

            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def _mark_build_failed(
        self,
        build_id: int,
        error: Exception,
        worker_started_at: float,
        worker_traceback: str,
    ) -> None:
        """Persist a terminal failure after an unexpected worker error."""
        build = self.db.get(Build, build_id)
        if build is None:
            return

        end_time = datetime.utcnow()
        duration = int(time.time() - worker_started_at)
        error_message = str(error)

        build.status = "failed"
        build.end_time = end_time
        build.duration = duration
        build.error_message = error_message

        incomplete_stages = (
            self.db.query(BuildStage)
            .filter(
                BuildStage.build_id == build_id,
                BuildStage.status.in_(["pending", "running"]),
            )
            .all()
        )
        for stage in incomplete_stages:
            stage.status = "failed"
            stage.finished_at = end_time
            stage.error_message = error_message
            if stage.started_at:
                stage.duration = int(
                    (end_time - stage.started_at).total_seconds()
                )
            else:
                stage.duration = 0

        self.db.commit()

        if build.log_path:
            runner = BuildRunner(
                workspace_dir=self.workspace_dir,
                logs_dir=self.logs_dir,
                timeout_seconds=self.timeout_seconds,
            )
            runner._log(
                build.log_path,
                f"=== Build #{build.id} Failed after {duration}s ===",
            )
            runner._log(build.log_path, f"Error: {error_message}")
            runner._log(
                build.log_path,
                f"Traceback:\n{worker_traceback}",
            )

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
