import os
import shlex
import subprocess
import time
import traceback
from datetime import datetime
from typing import Optional

from fastapi import BackgroundTasks, HTTPException
from sqlalchemy.orm import Session

from backend.common.database import SessionLocal
from backend.deploy.artifacts import (
    validate_docker_image,
    validate_health_check_path,
    validate_identifier,
    validate_port_mapping,
    validate_project_name,
    validate_remote_deploy_path,
    validate_remote_host,
    validate_remote_user,
    wait_for_http_health,
)
from backend.deploy.models import Deploy, DeployStage
from backend.deploy.schemas import (
    DeployExecutionInput,
    DeployResponse,
    DeployStartRequest,
)
from backend.deploy.ssh import SSHClient
from backend.deploy.strategies import get_registry
from backend.deploy.utils import get_log_path
from backend.project.models import Project


def run_deploy_worker(
    deploy_id: int,
    execution_data: dict,
) -> None:
    """Run a deploy with a database session owned by the background worker."""
    worker_started_at = time.time()

    try:
        execution = DeployExecutionInput.model_validate(execution_data)
        with SessionLocal() as db:
            service = DeployService(
                db=db,
                logs_dir=execution.logs_dir,
                workspace_dir=execution.workspace_dir,
                timeout_seconds=execution.timeout_seconds,
            )
            service._execute_deploy_sync(deploy_id, execution)
    except Exception as error:
        worker_traceback = traceback.format_exc()
        with SessionLocal() as db:
            service = DeployService(
                db=db,
                logs_dir=execution_data["logs_dir"],
                workspace_dir=execution_data["workspace_dir"],
                timeout_seconds=execution_data["timeout_seconds"],
            )
            service._mark_deploy_failed(
                deploy_id=deploy_id,
                error=error,
                worker_started_at=worker_started_at,
                worker_traceback=worker_traceback,
            )


class DeployService:
    def __init__(
        self,
        db: Session,
        logs_dir: str,
        workspace_dir: str = "workspace",
        timeout_seconds: int = 600,
        docker_enabled: bool = True,
        default_deploy_path: str = "/var/www/mini-cicd",
        default_service_name: str = "mini-cicd-app",
    ):
        self.db = db
        self.logs_dir = os.path.abspath(logs_dir)
        self.workspace_dir = os.path.abspath(workspace_dir)
        self.timeout_seconds = timeout_seconds
        self.docker_enabled = docker_enabled
        self.default_deploy_path = default_deploy_path
        self.default_service_name = default_service_name
        self.deadline = None

        # Stage tracking
        self.current_deploy_id = None
        self.stages = {}  # stage_name -> stage_id
        self.stage_logs = {}  # stage_name -> log_file_path

    def _remaining_timeout(self) -> float:
        if self.deadline is None:
            return float(self.timeout_seconds)

        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(
                f"Deploy timed out after {self.timeout_seconds} seconds"
            )
        return max(0.1, remaining)

    def _log_stage(self, stage_name: str, message: str) -> None:
        """Write message to stage-specific log file."""
        if stage_name in self.stage_logs:
            stage_log_file = self.stage_logs[stage_name]
            with open(stage_log_file, "a", encoding="utf-8") as f:
                f.write(f"{message}\n")

    def _create_stage_log_dir(self, deploy_id: int) -> str:
        """Create directory for stage logs."""
        stage_log_dir = os.path.join(self.logs_dir, f"deploy_{deploy_id}")
        os.makedirs(stage_log_dir, exist_ok=True)
        return stage_log_dir

    def _create_stage(self, deploy_id: int, stage_name: str) -> int:
        """Create a new deploy stage in database and return its ID."""
        stage_log_dir = self._create_stage_log_dir(deploy_id)
        stage_log_file = os.path.join(stage_log_dir, f"{stage_name.lower().replace(' ', '_')}.log")

        stage = DeployStage(
            deploy_id=deploy_id,
            stage_name=stage_name,
            status="pending",
            log_file=stage_log_file
        )

        self.db.add(stage)
        self.db.commit()
        self.db.refresh(stage)

        self.stages[stage_name] = stage.id
        self.stage_logs[stage_name] = stage_log_file

        return stage.id

    def _start_stage(self, stage_name: str) -> None:
        """Mark a stage as running."""
        if stage_name not in self.stages:
            return

        stage = self.db.query(DeployStage).filter(DeployStage.id == self.stages[stage_name]).first()
        if stage:
            stage.status = "running"
            stage.started_at = datetime.utcnow()
            self.db.commit()

    def _complete_stage(self, stage_name: str, status: str = "success", error_message: str = None) -> None:
        """Mark a stage as completed (success or failed)."""
        if stage_name not in self.stages:
            return

        stage = self.db.query(DeployStage).filter(DeployStage.id == self.stages[stage_name]).first()
        if stage:
            stage.status = status
            stage.finished_at = datetime.utcnow()
            if stage.started_at:
                stage.duration = int((stage.finished_at - stage.started_at).total_seconds())
            if error_message:
                stage.error_message = error_message
            self.db.commit()

    def _load_stages(self, deploy_id: int) -> None:
        """Load stage IDs and log paths into this worker-owned service."""
        stages = (
            self.db.query(DeployStage)
            .filter(DeployStage.deploy_id == deploy_id)
            .order_by(DeployStage.id)
            .all()
        )
        self.current_deploy_id = deploy_id
        self.stages = {stage.stage_name: stage.id for stage in stages}
        self.stage_logs = {
            stage.stage_name: stage.log_file
            for stage in stages
            if stage.log_file
        }

    def _initialize_stages(self, deploy_id: int, deploy_type: str, docker_mode: str = None) -> None:
        """Initialize all stages for a deploy."""
        self.current_deploy_id = deploy_id
        self.stages = {}
        self.stage_logs = {}

        # Common stages
        self._create_stage(deploy_id, "Validate Build")
        self._create_stage(deploy_id, "Connect to Server")

        if deploy_type == "docker":
            if docker_mode == "existing_image":
                self._create_stage(deploy_id, "Pull Docker Image")
            else:
                self._create_stage(deploy_id, "Transfer Docker Image")
            self._create_stage(deploy_id, "Run Docker Container")
        else:
            self._create_stage(deploy_id, "Upload Artifact")
            self._create_stage(deploy_id, "Execute Deploy Script")

        self._create_stage(deploy_id, "Finalize Deploy")

    def start_deploy(
        self,
        request: DeployStartRequest,
        background_tasks: BackgroundTasks,
    ) -> DeployResponse:
        """Create a deploy from canonical Build data and schedule its worker."""
        from backend.build.models import Build

        build = self.db.get(Build, request.build_id)
        if build is None:
            raise HTTPException(status_code=404, detail="Build not found")
        if build.status != "success":
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Build {build.id} is not successful. "
                    f"Current status: {build.status}"
                ),
            )

        project = self.db.get(Project, build.project_id)
        if project is None:
            raise HTTPException(
                status_code=404,
                detail="Project for this build no longer exists",
            )
        if project.status != "active":
            raise HTTPException(
                status_code=409,
                detail="Inactive projects cannot start new deploys",
            )

        request.server_ip = validate_remote_host(request.server_ip)
        request.server_user = validate_remote_user(request.server_user)
        validate_project_name(build.project_name)
        request.health_check_path = validate_health_check_path(
            request.health_check_path
        )
        request.port_mapping = validate_port_mapping(request.port_mapping)

        deploy_type = build.build_type
        if deploy_type not in {"source", "docker"}:
            raise HTTPException(
                status_code=409,
                detail=f"Unsupported build type: {deploy_type}",
            )

        docker_mode = build.docker_mode if deploy_type == "docker" else None
        deploy_path = None
        service_name = None
        image_name = None
        image_tag = None
        docker_image = None
        docker_compose_file = None

        if deploy_type == "docker":
            if not self.docker_enabled:
                raise HTTPException(
                    status_code=409,
                    detail="Docker execution is disabled in Settings",
                )
            if not request.container_name:
                raise HTTPException(
                    status_code=422,
                    detail="container_name is required for Docker deploy",
                )
            request.container_name = validate_identifier(
                request.container_name,
                "Container name",
            )

            if docker_mode == "existing_image":
                if not build.docker_image:
                    raise HTTPException(
                        status_code=409,
                        detail="Build does not contain an existing Docker image",
                    )
                docker_image = validate_docker_image(build.docker_image)
                docker_compose_file = build.docker_compose_file
            elif docker_mode == "build_from_git":
                if not build.image_name or not build.image_tag:
                    raise HTTPException(
                        status_code=409,
                        detail=(
                            "Docker build does not contain image_name "
                            "and image_tag"
                        ),
                    )
                image_name = build.image_name
                image_tag = build.image_tag
                validate_docker_image(f"{image_name}:{image_tag}")
            else:
                raise HTTPException(
                    status_code=409,
                    detail=f"Unsupported Docker mode: {docker_mode}",
                )
        else:
            deploy_path = (
                request.deploy_path
                or project.deploy_path
                or build.recommended_deploy_path
                or self.default_deploy_path
            )
            service_name = (
                request.service_name
                or project.service_name
                or build.recommended_service_name
                or self.default_service_name
            )
            deploy_path = validate_remote_deploy_path(deploy_path)
            service_name = validate_identifier(
                service_name,
                "Service name",
            )

        # Detector recommendations are displayed by the frontend, but they
        # must never execute unless the operator explicitly submits a script.
        deploy_script = request.deploy_script
        if deploy_type == "source":
            resolution = get_registry().resolve_strategy(
                build.detected_framework,
                build.detected_runtime,
                build.artifact_type,
            )
            if resolution.status == "experimental_disabled":
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"Deployment strategy {resolution.strategy.name} is "
                        "experimental and disabled. Set "
                        "MINI_CICD_ENABLE_EXPERIMENTAL_STRATEGIES=true "
                        "to enable it."
                    ),
                )
            if resolution.status == "artifact_mismatch":
                expected = ", ".join(
                    resolution.expected_artifact_types or []
                )
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "Build artifact is not supported by the detected "
                        f"deployment strategy. Expected: {expected}"
                    ),
                )
            if resolution.status == "unsupported":
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "No deployment strategy is available for "
                        f"framework={build.detected_framework}, "
                        f"runtime={build.detected_runtime}"
                    ),
                )

        deploy = Deploy(
            build_id=build.id,
            project_id=build.project_id,
            project_name=build.project_name,
            branch=build.branch,
            server_ip=request.server_ip,
            server_user=request.server_user,
            deploy_path=deploy_path,
            service_name=service_name,
            deploy_type=deploy_type,
            deploy_script=deploy_script,
            docker_mode=docker_mode,
            container_name=request.container_name,
            port_mapping=request.port_mapping,
            docker_image=docker_image,
            docker_compose_file=docker_compose_file,
            image_name=image_name,
            image_tag=image_tag,
            status="running",
            log_path=get_log_path(self.logs_dir, 0),
        )

        self.db.add(deploy)
        self.db.commit()
        self.db.refresh(deploy)

        deploy.log_path = get_log_path(self.logs_dir, deploy.id)
        self.db.commit()

        self._initialize_stages(deploy.id, deploy_type, docker_mode)

        self._log(deploy.log_path, f"=== Deploy #{deploy.id} Started ===")
        self._log(deploy.log_path, f"Build ID: {build.id}")
        self._log(deploy.log_path, f"Project: {build.project_name}")
        self._log(deploy.log_path, f"Branch: {build.branch}")
        self._log(deploy.log_path, f"Server: {request.server_user}@{request.server_ip}")
        self._log(deploy.log_path, f"Deploy Type: {deploy_type}")
        if deploy_type == "docker":
            self._log(deploy.log_path, f"Docker Mode: {docker_mode}")
            self._log(deploy.log_path, f"Container: {request.container_name}")
            if docker_mode == "existing_image":
                self._log(deploy.log_path, f"Docker Image: {docker_image}")
            else:
                self._log(deploy.log_path, f"Image: {image_name}:{image_tag}")
            if request.port_mapping:
                self._log(deploy.log_path, f"Port Mapping: {request.port_mapping}")
        else:
            self._log(deploy.log_path, f"Deploy Path: {deploy_path}")
            self._log(deploy.log_path, f"Service: {service_name}")

        execution = DeployExecutionInput(
            build_id=build.id,
            server_ip=request.server_ip,
            server_user=request.server_user,
            server_password=request.server_password,
            server_ssh_key=request.server_ssh_key,
            deploy_path=deploy_path,
            service_name=service_name,
            deploy_type=deploy_type,
            deploy_script=deploy_script,
            docker_mode=docker_mode,
            container_name=request.container_name,
            image_name=image_name,
            image_tag=image_tag,
            port_mapping=request.port_mapping,
            docker_image=docker_image,
            docker_compose_file=docker_compose_file,
            health_check_port=request.health_check_port,
            health_check_path=request.health_check_path or "/",
            workspace_dir=self.workspace_dir,
            logs_dir=self.logs_dir,
            timeout_seconds=self.timeout_seconds,
        )

        response = self._deploy_to_response(deploy)
        background_tasks.add_task(
            run_deploy_worker,
            deploy.id,
            execution.model_dump(),
        )
        return response

    def _execute_deploy_sync(
        self,
        deploy_id: int,
        request: DeployExecutionInput,
    ) -> None:
        """Execute a deploy using this worker's database session."""
        from backend.build.models import Build

        deploy = self.db.get(Deploy, deploy_id)
        if deploy is None:
            raise ValueError(f"Deploy {deploy_id} not found")

        build = self.db.get(Build, request.build_id)
        if build is None:
            raise ValueError(f"Build {request.build_id} not found")

        self._load_stages(deploy_id)
        start_time = time.time()
        self.deadline = time.monotonic() + self.timeout_seconds
        log_file = deploy.log_path
        ssh = None

        try:
            self._log(log_file, f"[DEBUG] _execute_deploy_sync started for deploy #{deploy.id}")
            self._log(log_file, f"[DEBUG] Request details: deploy_type={request.deploy_type}, server={request.server_ip}")

            self._start_stage("Validate Build")
            self._log_stage("Validate Build", f"Validating build #{request.build_id}...")
            self._log(log_file, "Step 1: Getting build record...")
            self._log(log_file, f"Build record found: artifact_path={build.artifact_path}, artifact_type={build.artifact_type}")
            self._log_stage(
                "Validate Build",
                f"Build validated: artifact_path={build.artifact_path}, artifact_type={build.artifact_type}",
            )
            self._complete_stage("Validate Build", "success")

            self._start_stage("Connect to Server")
            self._log_stage("Connect to Server", f"Initializing SSH client for {request.server_user}@{request.server_ip}...")
            self._log(log_file, "Step 2: Initializing SSH client...")
            self._log(log_file, f"Step 2: Host: {request.server_ip}, User: {request.server_user}")
            self._log(log_file, f"Step 2: Using password: {'Yes' if request.server_password else 'No'}")
            self._log(log_file, f"Step 2: Using SSH key: {'Yes' if request.server_ssh_key else 'No'}")
            ssh = SSHClient(
                host=request.server_ip,
                username=request.server_user,
                password=request.server_password,
                key=request.server_ssh_key,
                timeout_seconds=self.timeout_seconds,
                deadline=self.deadline,
            )

            self._log(log_file, f"Step 3: Connecting to SSH server {request.server_user}@{request.server_ip}...")
            self._log_stage("Connect to Server", "Connecting to SSH server...")
            self._log(
                log_file,
                (
                    "Step 3: Attempting SSH connection "
                    f"(deploy deadline={self.timeout_seconds}s)..."
                ),
            )
            success, error = ssh.connect()
            if not success:
                self._log(log_file, f"Step 3: SSH connection failed: {error}")
                self._log_stage("Connect to Server", f"SSH connection failed: {error}")
                self._complete_stage("Connect to Server", "failed", error)
                raise RuntimeError(error)

            self._log(log_file, "Step 3: SSH connection established successfully")
            self._log_stage("Connect to Server", "SSH connection established successfully")
            self._complete_stage("Connect to Server", "success")

            if request.deploy_type == "docker":
                self._execute_docker_deploy(ssh, deploy, request, build, log_file)
            else:
                self._execute_source_deploy(ssh, deploy, request, build, log_file)

            self._start_stage("Finalize Deploy")
            self._log_stage("Finalize Deploy", "Updating deploy record...")
            self._log(log_file, "Step 8: Updating deploy record...")
            end_time = datetime.utcnow()
            duration = int(time.time() - start_time)

            deploy.status = "success"
            deploy.end_time = end_time
            deploy.duration = duration
            deploy.error_message = None
            self.db.commit()
            self._log(log_file, "Step 8: Deploy record updated successfully")
            self._log(log_file, f"=== Deploy #{deploy.id} Completed Successfully in {duration}s ===")
            self._log_stage("Finalize Deploy", f"Deploy completed successfully in {duration}s")
            self._complete_stage("Finalize Deploy", "success")
        except Exception:
            self.db.rollback()
            raise
        finally:
            if ssh is not None:
                try:
                    self._log(log_file, "Step 7: Closing SSH connection...")
                    ssh.close()
                    self._log(log_file, "Step 7: SSH connection closed")
                except Exception as close_error:
                    self._log(log_file, f"Failed to close SSH connection cleanly: {close_error}")

    def _mark_deploy_failed(
        self,
        deploy_id: int,
        error: Exception,
        worker_started_at: float,
        worker_traceback: str,
    ) -> None:
        """Persist a terminal failure after an unexpected worker error."""
        deploy = self.db.get(Deploy, deploy_id)
        if deploy is None:
            return

        end_time = datetime.utcnow()
        duration = int(time.time() - worker_started_at)
        error_message = str(error)

        deploy.status = "failed"
        deploy.end_time = end_time
        deploy.duration = duration
        deploy.error_message = error_message

        incomplete_stages = (
            self.db.query(DeployStage)
            .filter(
                DeployStage.deploy_id == deploy_id,
                DeployStage.status.in_(["pending", "running"]),
            )
            .all()
        )
        for stage in incomplete_stages:
            stage.status = "failed"
            stage.finished_at = end_time
            stage.error_message = error_message
            if stage.started_at:
                stage.duration = int((end_time - stage.started_at).total_seconds())
            else:
                stage.duration = 0

        self.db.commit()

        if deploy.log_path:
            self._log(deploy.log_path, f"=== Deploy #{deploy.id} Failed after {duration}s ===")
            self._log(deploy.log_path, f"Error: {error_message}")
            self._log(deploy.log_path, f"Traceback:\n{worker_traceback}")

    def _execute_source_deploy(
        self,
        ssh: SSHClient,
        deploy: Deploy,
        request: DeployExecutionInput,
        build,
        log_file: str
    ) -> None:
        """Execute source-based deployment using strategy-based approach."""
        from backend.deploy.strategies import DeploymentContext

        # Upload Artifact stage
        self._start_stage("Upload Artifact")
        self._log_stage("Upload Artifact", "Uploading artifact to remote server...")

        # Check if custom deploy script is provided
        if request.deploy_script:
            self._log(log_file, f"Step 4: Using custom deploy script, skipping strategy-based deployment")
            if build and build.artifact_path and build.artifact_type != "docker_image":
                self._log(log_file, f"Step 4: Uploading artifact...")
                artifact_type = build.artifact_type or "file"
                self._upload_artifact(
                    ssh, build.artifact_path, artifact_type,
                    request.deploy_path, request.service_name, log_file
                )
                self._log(log_file, f"Step 4: Artifact upload completed")
                self._log_stage("Upload Artifact", "Artifact uploaded successfully")
            else:
                self._log_stage("Upload Artifact", "No artifact to upload for custom script mode")
            self._complete_stage("Upload Artifact", "success")

            # Execute Deploy Script stage
            self._start_stage("Execute Deploy Script")
            self._log_stage("Execute Deploy Script", "Executing custom deploy script...")
            self._log(log_file, f"Step 5: Executing custom deploy script...")
            self._execute_custom_script(ssh, request.deploy_script, request.deploy_path, log_file)
            self._log(log_file, f"Step 5: Custom deploy script execution completed")
            self._log_stage("Execute Deploy Script", "Custom deploy script executed successfully")
            self._complete_stage("Execute Deploy Script", "success")
            return

        # Use strategy-based deployment
        self._log(log_file, f"Step 4: Using strategy-based deployment")

        # Get detected framework and runtime from build metadata
        framework = build.detected_framework if build else None
        runtime = build.detected_runtime if build else None

        self._log(log_file, f"Detected Framework: {framework}")
        self._log(log_file, f"Detected Runtime: {runtime}")

        resolution = get_registry().resolve_strategy(
            framework,
            runtime,
            build.artifact_type if build else None,
        )
        strategy = resolution.strategy if resolution.status in {
            "verified",
            "experimental_enabled",
        } else None

        if strategy:
            self._log(log_file, f"Using deployment strategy: {strategy.name}")

            # Convert relative artifact_path to absolute path
            artifact_path = None
            if build and build.artifact_path:
                artifact_path = build.artifact_path
                # If artifact_path is relative, convert to absolute path using workspace_dir
                if not os.path.isabs(artifact_path):
                    artifact_path = os.path.join(self.workspace_dir, artifact_path)
                    self._log(log_file, f"Converted artifact path to absolute: {artifact_path}")

            # Debug logging before upload
            self._log(log_file, f"DEBUG: artifact_path = {artifact_path}")
            self._log(log_file, f"DEBUG: exists = {os.path.exists(artifact_path) if artifact_path else 'N/A'}")
            self._log(log_file, f"DEBUG: isfile = {os.path.isfile(artifact_path) if artifact_path else 'N/A'}")
            self._log(log_file, f"DEBUG: isdir = {os.path.isdir(artifact_path) if artifact_path else 'N/A'}")

            # Create deployment context
            context = DeploymentContext(
                ssh_client=ssh,
                deploy_path=request.deploy_path,
                service_name=request.service_name,
                artifact_path=artifact_path,
                artifact_type=build.artifact_type if build else None,
                project_name=build.project_name if build else None,
                additional_params={'framework': framework},
                workspace_dir=self.workspace_dir,
                release_id=str(deploy.id),
                health_check_port=request.health_check_port,
                health_check_path=request.health_check_path,
            )

            # Execute strategy
            success = strategy.execute(context, lambda msg: self._log(log_file, msg))

            if success:
                self._log(log_file, f"Step 4: Strategy-based deployment completed successfully")
                self._log_stage("Upload Artifact", "Artifact uploaded successfully via strategy")
                self._complete_stage("Upload Artifact", "success")

                # Perform post-deployment validation
                self._log(log_file, f"Step 5: Validating deployment...")
                validation_success = strategy.validate(context, lambda msg: self._log(log_file, msg))

                if validation_success:
                    self._log(log_file, f"Step 5: Deployment validation passed")
                    self._start_stage("Execute Deploy Script")
                    self._log_stage(
                        "Execute Deploy Script",
                        "Deployment strategy handled execution; no custom script was required.",
                    )
                    self._complete_stage(
                        "Execute Deploy Script",
                        "success",
                    )
                else:
                    self._log(log_file, f"Step 5: Deployment validation failed")
                    raise Exception("Deployment validation failed")
            else:
                self._log(log_file, f"Step 4: Strategy-based deployment failed")
                raise Exception("Strategy-based deployment failed")
        else:
            self._log(log_file, f"No suitable deployment strategy found for framework={framework}, runtime={runtime}")
            self._log(log_file, f"ERROR: Unsupported framework/runtime combination")
            supported = [
                capability["name"]
                for capability in get_registry().list_capabilities()
                if capability["enabled"]
            ]
            self._log(log_file, f"Enabled deployment profiles: {supported}")
            raise Exception(
                "Deployment strategy unavailable "
                f"(status={resolution.status}) for framework={framework}, "
                f"runtime={runtime}, artifact_type={build.artifact_type if build else None}"
            )

    def _execute_docker_deploy(
        self,
        ssh: SSHClient,
        deploy: Deploy,
        request: DeployExecutionInput,
        build,
        log_file: str
    ) -> None:
        """Execute Docker-based deployment (save/load image + run container OR pull existing image)."""

        # Handle existing docker image mode
        if request.docker_mode == "existing_image":
            docker_image = request.docker_image
            self._start_stage("Pull Docker Image")
            self._log_stage("Pull Docker Image", f"Pulling Docker image {docker_image} from registry...")
            self._log(log_file, f"Step 4: Pulling Docker image {docker_image} from registry...")
            self._pull_docker_image(ssh, docker_image, log_file)
            self._log(log_file, f"Step 4: Docker image pulled successfully")
            self._log_stage("Pull Docker Image", f"Docker image pulled successfully: {docker_image}")
            self._complete_stage("Pull Docker Image", "success")
            full_image = docker_image
        else:
            # build_from_git mode - transfer image from local build
            image_name = deploy.image_name
            image_tag = deploy.image_tag or "latest"
            full_image = f"{image_name}:{image_tag}"

            self._start_stage("Transfer Docker Image")
            self._log_stage("Transfer Docker Image", f"Transferring Docker image {full_image} to remote server...")
            self._log(log_file, f"Step 4: Transferring Docker image {full_image} to remote server...")
            self._transfer_docker_image(ssh, full_image, deploy.id, log_file)
            self._log(log_file, f"Step 4: Docker image transferred successfully")
            self._log_stage("Transfer Docker Image", f"Docker image transferred successfully")
            self._complete_stage("Transfer Docker Image", "success")

        # Run Docker Container stage
        self._start_stage("Run Docker Container")
        self._log_stage("Run Docker Container", "Deploying Docker container...")
        self._log(log_file, f"Step 5: Deploying Docker container...")
        if request.deploy_script:
            self._execute_custom_script(ssh, request.deploy_script, None, log_file)
        else:
            self._run_docker_container(ssh, request, deploy, log_file, full_image)
        self._log(log_file, f"Step 5: Docker deployment completed")
        self._log_stage("Run Docker Container", "Docker container deployed successfully")
        self._complete_stage("Run Docker Container", "success")

        self._log(log_file, f"Step 6: Validating Docker deployment...")
        container_name = request.container_name
        
        # Check if container is running
        self._log(log_file, f"Validating container {container_name}...")
        success, stdout, stderr = ssh.execute_command(
            "docker ps "
            f"--filter {shlex.quote(f'name=^{container_name}$')} "
            "--format '{{.Names}} {{.Status}}'"
        )
        if success and stdout.strip():
            self._log(log_file, f"✓ Container running: {stdout.strip()}")
        else:
            self._log(log_file, f"✗ Container not running")
            self._log(log_file, f"  stdout: {stdout}")
            self._log(log_file, f"  stderr: {stderr}")
            raise Exception(f"Container {container_name} is not running")
        
        # Check container health status if available
        self._log(log_file, f"Validating container health status...")
        success, stdout, stderr = ssh.execute_command(
            "docker inspect --format='{{.State.Health.Status}}' "
            f"{shlex.quote(container_name)} "
            "2>/dev/null || echo 'no-healthcheck'"
        )
        if success and stdout.strip() and stdout.strip() != "no-healthcheck":
            health_status = stdout.strip()
            if health_status == "healthy":
                self._log(log_file, f"✓ Container health: {health_status}")
            elif health_status == "starting":
                self._log(log_file, f"⚠ Container health: {health_status}")
            else:
                self._log(log_file, f"✗ Container health: {health_status}")
                self._log(log_file, f"  Container may not be healthy")
        else:
            self._log(log_file, f"✓ No health check configured")

        if request.health_check_port and not wait_for_http_health(
            ssh,
            request.health_check_port,
            request.health_check_path,
        ):
            raise Exception(
                "Docker HTTP health check failed on "
                f"127.0.0.1:{request.health_check_port}"
                f"{request.health_check_path}"
            )
        
        self._log(log_file, f"Step 6: Docker deployment validation passed")

    def _transfer_docker_image(
        self,
        ssh: SSHClient,
        full_image: str,
        deploy_id: int,
        log_file: str
    ) -> None:
        """
        Export Docker image locally, upload via SFTP, and load on remote server.
        """
        local_tar = os.path.join(self.logs_dir, f"docker_image_{deploy_id}.tar")
        remote_tar = f"/tmp/docker_image_{deploy_id}.tar"

        self._log(log_file, f"Saving Docker image locally: {full_image}")
        try:
            result = subprocess.run(
                ["docker", "save", "-o", local_tar, full_image],
                capture_output=True,
                text=True,
                timeout=self._remaining_timeout(),
            )
            if result.returncode != 0:
                raise Exception(f"docker save failed: {result.stderr or result.stdout}")

            tar_size_mb = os.path.getsize(local_tar) / (1024 * 1024)
            self._log(log_file, f"Image saved to {local_tar} ({tar_size_mb:.1f} MB)")
        except subprocess.TimeoutExpired:
            raise Exception(
                f"docker save timed out after {self.timeout_seconds} seconds"
            )
        except FileNotFoundError:
            raise Exception("Docker CLI not found on CI server. Install Docker to deploy images.")

        try:
            self._log(log_file, f"Uploading image to remote server: {remote_tar}")
            success, error = ssh.upload_file(local_tar, remote_tar)
            if not success:
                raise Exception(f"Image upload failed: {error}")
            self._log(log_file, f"Image uploaded successfully")

            self._log(log_file, f"Loading Docker image on remote server...")
            success, stdout, stderr = ssh.execute_command(
                f"docker load -i {shlex.quote(remote_tar)}"
            )
            if stdout:
                self._log(log_file, f"STDOUT:\n{stdout}")
            if stderr:
                self._log(log_file, f"STDERR:\n{stderr}")
            if not success:
                raise Exception(f"docker load failed on remote server: {stderr}")

            self._log(log_file, f"Docker image loaded on remote server")

            ssh.execute_command(f"rm -f -- {shlex.quote(remote_tar)}")
        finally:
            if os.path.exists(local_tar):
                os.remove(local_tar)
                self._log(log_file, f"Cleaned up local image tar")

    def _pull_docker_image(
        self,
        ssh: SSHClient,
        docker_image: str,
        log_file: str
    ) -> None:
        """
        Pull Docker image from registry on remote server.
        """
        self._log(log_file, f"Pulling Docker image on remote server: {docker_image}")
        docker_image = validate_docker_image(docker_image)
        success, stdout, stderr = ssh.execute_command(
            f"docker pull {shlex.quote(docker_image)}"
        )
        if stdout:
            self._log(log_file, f"STDOUT:\n{stdout}")
        if stderr:
            self._log(log_file, f"STDERR:\n{stderr}")
        if not success:
            raise Exception(f"docker pull failed on remote server: {stderr}")
        self._log(log_file, f"Docker image pulled successfully on remote server")

    def _run_docker_container(
        self,
        ssh: SSHClient,
        request: DeployExecutionInput,
        deploy: Deploy,
        log_file: str,
        full_image: str
    ) -> None:
        """Stop existing container (if any) and run a new one."""
        container_name = request.container_name
        quoted_container_name = shlex.quote(container_name)
        full_image = validate_docker_image(full_image)

        self._log(log_file, f"Stopping existing container (if any): {container_name}")
        ssh.execute_command(
            f"docker stop {quoted_container_name} 2>/dev/null || true"
        )
        ssh.execute_command(
            f"docker rm {quoted_container_name} 2>/dev/null || true"
        )

        run_cmd = (
            "docker run -d "
            f"--name {quoted_container_name} --restart unless-stopped"
        )
        if request.port_mapping:
            port_mapping = validate_port_mapping(request.port_mapping)
            run_cmd += f" -p {shlex.quote(port_mapping)}"
        run_cmd += f" {shlex.quote(full_image)}"

        self._log(log_file, f"Running container: {run_cmd}")
        success, stdout, stderr = ssh.execute_command(run_cmd)
        if stdout:
            self._log(log_file, f"STDOUT:\n{stdout}")
        if stderr:
            self._log(log_file, f"STDERR:\n{stderr}")
        if not success:
            raise Exception(f"docker run failed: {stderr}")

        self._log(log_file, f"Container {container_name} started with image {full_image}")

    def _execute_custom_script(self, ssh: SSHClient, deploy_script: str, deploy_path: Optional[str], log_file: str) -> None:
        """
        Execute custom deploy script commands sequentially.
        
        Args:
            ssh: SSH client instance
            deploy_script: Custom deploy script with multiple commands
            deploy_path: Deployment path
            log_file: Log file path
        """
        self._log(log_file, "Executing custom deploy script...")
        
        # Split script into commands (one per line)
        commands = [cmd.strip() for cmd in deploy_script.splitlines() if cmd.strip()]
        
        for i, cmd in enumerate(commands, 1):
            self._log(log_file, f"\n=== Executing Command {i}/{len(commands)} ===")
            self._log(
                log_file,
                f"Executing custom command {i}; command text is redacted",
            )
            
            # Execute command with optional deploy path context
            if deploy_path:
                safe_deploy_path = validate_remote_deploy_path(deploy_path)
                full_cmd = f"cd {shlex.quote(safe_deploy_path)} && {cmd}"
            else:
                full_cmd = cmd
            success, stdout, stderr = ssh.execute_command(full_cmd)
            
            # Log output
            if stdout:
                self._log(log_file, f"STDOUT:\n{stdout}")
            if stderr:
                self._log(log_file, f"STDERR:\n{stderr}")
            
            # Check if command failed
            if not success:
                raise Exception(f"Custom command {i} failed: {stderr}")
            
            self._log(log_file, f"Command {i} completed successfully")
        
        self._log(log_file, f"All commands completed successfully")

    def get_deploy_status(self, deploy_id: int) -> Optional[DeployResponse]:
        """
        Get deploy status by ID.
        
        Args:
            deploy_id: Deploy ID
            
        Returns:
            Deploy response or None if not found
        """
        deploy = self.db.query(Deploy).filter(Deploy.id == deploy_id).first()
        if not deploy:
            return None
        
        return self._deploy_to_response(deploy)

    def get_deploy_log(self, deploy_id: int) -> Optional[str]:
        """
        Get deploy log content.
        
        Args:
            deploy_id: Deploy ID
            
        Returns:
            Log content or None if not found
        """
        deploy = self.db.query(Deploy).filter(Deploy.id == deploy_id).first()
        if not deploy or not deploy.log_path:
            return None
        
        if not os.path.exists(deploy.log_path):
            return "Log file not found"
        
        try:
            with open(deploy.log_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Error reading log file: {str(e)}"

    def get_deploy_history(
        self,
        project_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0
    ) -> tuple[list[DeployResponse], int]:
        """
        Get deploy history with optional filtering.
        
        Args:
            project_id: Filter by project ID (optional)
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            Tuple of (deploys list, total count)
        """
        query = self.db.query(Deploy)
        
        if project_id:
            query = query.filter(Deploy.project_id == project_id)
        
        total = query.count()
        deploys = query.order_by(Deploy.id.desc()).offset(offset).limit(limit).all()
        
        return [self._deploy_to_response(deploy) for deploy in deploys], total

    def _log(self, log_file: str, message: str) -> None:
        """Write message to log file."""
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"{message}\n")

    def _upload_artifact(self, ssh: SSHClient, artifact_path: str, artifact_type: str, deploy_path: str, service_name: str, log_file: str) -> None:
        """Upload an artifact for an explicitly supplied custom script."""
        from backend.deploy.artifacts import transfer_artifact

        remote_path = transfer_artifact(
            ssh,
            artifact_path,
            artifact_type,
            deploy_path,
            lambda message: self._log(log_file, message),
            workspace_dir=self.workspace_dir,
        )
        self._log(log_file, f"Artifact available at {remote_path}")

    def _deploy_to_response(self, deploy: Deploy) -> DeployResponse:
        """
        Convert Deploy model to DeployResponse schema.

        Args:
            deploy: Deploy model instance

        Returns:
            DeployResponse schema
        """
        return DeployResponse(
            id=deploy.id,
            build_id=deploy.build_id,
            project_id=deploy.project_id,
            project_name=deploy.project_name,
            branch=deploy.branch,
            server_ip=deploy.server_ip,
            server_user=deploy.server_user,
            deploy_path=deploy.deploy_path,
            service_name=deploy.service_name,
            deploy_type=deploy.deploy_type,
            deploy_script=deploy.deploy_script,
            docker_mode=deploy.docker_mode,
            container_name=deploy.container_name,
            image_name=deploy.image_name,
            image_tag=deploy.image_tag,
            port_mapping=deploy.port_mapping,
            docker_image=deploy.docker_image,
            docker_compose_file=deploy.docker_compose_file,
            status=deploy.status,
            start_time=deploy.start_time,
            end_time=deploy.end_time,
            duration=deploy.duration,
            log_path=deploy.log_path,
            error_message=deploy.error_message
        )

    def get_deploy_stages(self, deploy_id: int):
        """
        Get all stages for a deploy.

        Args:
            deploy_id: Deploy ID

        Returns:
            List of DeployStageResponse schemas or None if deploy not found
        """
        from backend.deploy.models import DeployStage
        from backend.deploy.schemas import DeployStageResponse

        # Check if deploy exists
        deploy = self.db.query(Deploy).filter(Deploy.id == deploy_id).first()
        if not deploy:
            return None

        # Get all stages for this deploy
        stages = self.db.query(DeployStage).filter(DeployStage.deploy_id == deploy_id).order_by(DeployStage.id).all()

        return [DeployStageResponse(
            id=stage.id,
            deploy_id=stage.deploy_id,
            stage_name=stage.stage_name,
            status=stage.status,
            started_at=stage.started_at,
            finished_at=stage.finished_at,
            duration=stage.duration,
            log_file=stage.log_file,
            error_message=stage.error_message
        ) for stage in stages]

    def get_stage_log(self, deploy_id: int, stage_name: str):
        """
        Get log content for a specific stage.

        Args:
            deploy_id: Deploy ID
            stage_name: Stage name

        Returns:
            Log content as string or None if not found
        """
        from backend.deploy.models import DeployStage

        # Find the stage
        stage = self.db.query(DeployStage).filter(
            DeployStage.deploy_id == deploy_id,
            DeployStage.stage_name == stage_name
        ).first()

        if not stage or not stage.log_file:
            return None

        # Read the log file
        try:
            with open(stage.log_file, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return None
