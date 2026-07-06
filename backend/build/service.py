import os
import time
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from backend.build.models import Build
from backend.build.schemas import BuildStartRequest, BuildResponse
from backend.build.runner import BuildRunner
from backend.build.utils import get_log_path


class BuildService:
    def __init__(self, db: Session, workspace_dir: str, logs_dir: str):
        self.db = db
        self.workspace_dir = workspace_dir
        self.logs_dir = logs_dir
        self.runner = BuildRunner(workspace_dir, logs_dir)

    def start_build(self, request: BuildStartRequest) -> BuildResponse:
        """
        Start a new build process.
        
        Args:
            request: Build start request with project details
            
        Returns:
            Build response with build details
        """
        # Create build record
        build = Build(
            project_id=request.project_id,
            project_name=request.project_name,
            branch=request.branch,
            deploy_type=request.deploy_type,
            build_script=request.build_script,
            status="running",
            log_path=get_log_path(self.logs_dir, 0)  # Temporary, will update after getting ID
        )
        
        self.db.add(build)
        self.db.commit()
        self.db.refresh(build)
        
        # Update log path with actual build ID
        build.log_path = get_log_path(self.logs_dir, build.id)
        self.db.commit()
        
        # Execute build asynchronously (in production, use Celery or similar)
        # For now, run synchronously
        self._execute_build_sync(build, request.git_url)
        
        return self._build_to_response(build)

    def _execute_build_sync(self, build: Build, git_url: str) -> None:
        """
        Execute build synchronously.
        
        Args:
            build: Build model instance
            git_url: Git repository URL
        """
        start_time = time.time()
        
        try:
            success, commit_hash, error_message = self.runner.execute_build(
                git_url=git_url,
                project_name=build.project_name,
                branch=build.branch,
                build_id=build.id
            )
            
            # Update build record
            end_time = datetime.utcnow()
            duration = int(time.time() - start_time)
            
            build.status = "success" if success else "failed"
            build.commit_hash = commit_hash
            build.end_time = end_time
            build.duration = duration
            
            if not success:
                build.error_message = error_message
            
            self.db.commit()
            
        except Exception as e:
            # Handle unexpected errors
            end_time = datetime.utcnow()
            duration = int(time.time() - start_time)
            
            build.status = "failed"
            build.end_time = end_time
            build.duration = duration
            build.error_message = f"Unexpected error: {str(e)}"
            
            self.db.commit()

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
            deploy_type=build.deploy_type,
            build_script=build.build_script,
            status=build.status,
            start_time=build.start_time,
            end_time=build.end_time,
            duration=build.duration,
            log_path=build.log_path,
            error_message=build.error_message
        )
