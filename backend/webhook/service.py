import hashlib
import hmac
import re
from datetime import datetime
from typing import Any, Optional
from urllib.parse import urlparse

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.build.models import Build
from backend.build.schemas import BuildStartRequest
from backend.build.service import BuildService, run_build_worker
from backend.common.database import SessionLocal
from backend.common.runtime import get_execution_settings
from backend.deploy.models import Deploy
from backend.deploy.schemas import DeployStartRequest
from backend.deploy.service import DeployService, run_deploy_worker
from backend.deploy.ssh import SSHClient
from backend.project.models import Project
from backend.settings.service import get_settings
from backend.webhook.models import (
    DeploymentTargetSettings,
    ProjectAutomationConfig,
    WebhookDelivery,
)
from backend.webhook.schemas import (
    DeploymentTargetResponse,
    DeploymentTargetTestResponse,
    DeploymentTargetUpdate,
    ProjectAutomationResponse,
    ProjectAutomationUpdate,
)


ACTIVE_DELIVERY_STATUSES = ("queued", "building", "deploying")
COMMIT_SHA_PATTERN = re.compile(r"^[0-9a-fA-F]{40}$")


def verify_github_signature(secret: str, body: bytes, signature: str) -> bool:
    if not signature.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def normalize_github_repository(value: Optional[str]) -> Optional[str]:
    if not value:
        return None

    candidate = value.strip()
    if not candidate:
        return None

    if candidate.lower().startswith("git@github.com:"):
        path = candidate.split(":", 1)[1]
    elif re.fullmatch(
        r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?",
        candidate,
    ):
        path = candidate
    else:
        parsed = urlparse(candidate)
        if (parsed.hostname or "").lower() != "github.com":
            return None
        path = parsed.path

    parts = [part for part in path.strip("/").split("/") if part]
    if len(parts) != 2:
        return None

    owner, repository = parts
    repository = repository.removesuffix(".git")
    if not owner or not repository:
        return None
    return f"{owner}/{repository}".lower()


def validate_commit_sha(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str) or not COMMIT_SHA_PATTERN.fullmatch(value):
        raise ValueError("GitHub commit SHA must contain 40 hexadecimal characters")
    return value.lower()


def get_deployment_target(db: Session) -> Optional[DeploymentTargetSettings]:
    return (
        db.query(DeploymentTargetSettings)
        .order_by(DeploymentTargetSettings.id.asc())
        .first()
    )


def deployment_target_response(
    target: Optional[DeploymentTargetSettings],
) -> DeploymentTargetResponse:
    if target is None:
        return DeploymentTargetResponse(configured=False)
    return DeploymentTargetResponse(
        id=target.id,
        configured=True,
        host=target.host,
        port=target.port,
        server_user=target.server_user,
        private_key_path=target.private_key_path,
        known_hosts_path=target.known_hosts_path,
        created_at=target.created_at,
        updated_at=target.updated_at,
    )


def update_deployment_target(
    db: Session,
    data: DeploymentTargetUpdate,
) -> DeploymentTargetResponse:
    target = get_deployment_target(db)
    values = data.model_dump()
    if target is None:
        target = DeploymentTargetSettings(**values)
        db.add(target)
    else:
        for field, value in values.items():
            setattr(target, field, value)
    db.commit()
    db.refresh(target)
    return deployment_target_response(target)


def test_deployment_target(db: Session) -> DeploymentTargetTestResponse:
    target = get_deployment_target(db)
    if target is None:
        raise HTTPException(status_code=409, detail="Deployment target is not configured")

    ssh = SSHClient(
        host=target.host,
        port=target.port,
        username=target.server_user,
        key=target.private_key_path,
        known_hosts_path=target.known_hosts_path,
        timeout_seconds=15,
    )
    try:
        success, error = ssh.connect()
        if not success:
            return DeploymentTargetTestResponse(success=False, message=error)
        success, _, error = ssh.execute_command("true")
        if not success:
            return DeploymentTargetTestResponse(
                success=False,
                message=error or "SSH command check failed",
            )
        return DeploymentTargetTestResponse(
            success=True,
            message="SSH connection succeeded",
        )
    finally:
        ssh.close()


def _default_automation_response(project_id: int) -> ProjectAutomationResponse:
    return ProjectAutomationResponse(
        project_id=project_id,
        configured=False,
        enabled=False,
        build_type="source",
        health_check_path="/",
    )


def get_project_automation(
    db: Session,
    project_id: int,
) -> ProjectAutomationResponse:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    config = (
        db.query(ProjectAutomationConfig)
        .filter(ProjectAutomationConfig.project_id == project_id)
        .first()
    )
    if config is None:
        return _default_automation_response(project_id)
    return ProjectAutomationResponse.model_validate(
        {
            **{
                column.name: getattr(config, column.name)
                for column in ProjectAutomationConfig.__table__.columns
            },
            "configured": True,
        }
    )


def _find_conflicting_project(
    db: Session,
    project: Project,
    *,
    repo_url: Optional[str] = None,
    branch: Optional[str] = None,
    status: Optional[str] = None,
) -> Optional[Project]:
    effective_status = status or project.status
    if effective_status != "active":
        return None

    repository = normalize_github_repository(repo_url or project.repo_url)
    effective_branch = branch or project.branch
    if repository is None:
        raise HTTPException(
            status_code=422,
            detail="Webhook automation requires a github.com repository URL",
        )

    enabled_configs = (
        db.query(ProjectAutomationConfig)
        .filter(
            ProjectAutomationConfig.enabled.is_(True),
            ProjectAutomationConfig.project_id != project.id,
        )
        .all()
    )
    for config in enabled_configs:
        other = db.get(Project, config.project_id)
        if (
            other is not None
            and other.status == "active"
            and other.branch == effective_branch
            and normalize_github_repository(other.repo_url) == repository
        ):
            return other
    return None


def ensure_project_automation_unique(
    db: Session,
    project: Project,
    *,
    repo_url: Optional[str] = None,
    branch: Optional[str] = None,
    status: Optional[str] = None,
) -> None:
    config = (
        db.query(ProjectAutomationConfig)
        .filter(ProjectAutomationConfig.project_id == project.id)
        .first()
    )
    if config is None or not config.enabled:
        return
    conflict = _find_conflicting_project(
        db,
        project,
        repo_url=repo_url,
        branch=branch,
        status=status,
    )
    if conflict is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                "Another active project already has automation enabled for "
                f"this repository and branch: {conflict.name}"
            ),
        )


def update_project_automation(
    db: Session,
    project_id: int,
    data: ProjectAutomationUpdate,
) -> ProjectAutomationResponse:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    if data.enabled:
        repository = normalize_github_repository(project.repo_url)
        if repository is None:
            raise HTTPException(
                status_code=422,
                detail="Webhook automation requires a github.com repository URL",
            )
        conflict = _find_conflicting_project(db, project)
        if conflict is not None:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Another active project already has automation enabled for "
                    f"this repository and branch: {conflict.name}"
                ),
            )

    config = (
        db.query(ProjectAutomationConfig)
        .filter(ProjectAutomationConfig.project_id == project_id)
        .first()
    )
    values = data.model_dump()
    if config is None:
        config = ProjectAutomationConfig(project_id=project_id, **values)
        db.add(config)
    else:
        for field, value in values.items():
            setattr(config, field, value)
    db.commit()
    db.refresh(config)
    return get_project_automation(db, project_id)


def delete_project_automation(db: Session, project_id: int) -> None:
    db.query(ProjectAutomationConfig).filter(
        ProjectAutomationConfig.project_id == project_id
    ).delete(synchronize_session=False)


def get_deliveries(
    db: Session,
    *,
    status: Optional[str] = None,
    project_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[WebhookDelivery], int]:
    query = db.query(WebhookDelivery)
    if status:
        query = query.filter(WebhookDelivery.status == status)
    if project_id:
        query = query.filter(WebhookDelivery.project_id == project_id)
    total = query.count()
    deliveries = (
        query.order_by(WebhookDelivery.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return deliveries, total


def get_delivery(db: Session, delivery_id: int) -> Optional[WebhookDelivery]:
    return db.get(WebhookDelivery, delivery_id)


def _match_project(
    db: Session,
    repository: str,
    branch: str,
) -> tuple[Optional[Project], Optional[ProjectAutomationConfig], str]:
    repository_projects = [
        project
        for project in db.query(Project).all()
        if normalize_github_repository(project.repo_url) == repository
    ]
    branch_projects = [
        project for project in repository_projects if project.branch == branch
    ]
    if not repository_projects:
        return None, None, "No Project matches this GitHub repository"
    if not branch_projects:
        return None, None, "Push branch does not match the configured Project branch"

    active_projects = [
        project for project in branch_projects if project.status == "active"
    ]
    if not active_projects:
        return None, None, "Matching Project is inactive"

    matches: list[tuple[Project, ProjectAutomationConfig]] = []
    for project in active_projects:
        config = (
            db.query(ProjectAutomationConfig)
            .filter(
                ProjectAutomationConfig.project_id == project.id,
                ProjectAutomationConfig.enabled.is_(True),
            )
            .first()
        )
        if config is not None:
            matches.append((project, config))

    if not matches:
        return None, None, "Automation is not enabled for the matching Project"
    if len(matches) > 1:
        return None, None, "Multiple active Projects match this repository and branch"
    project, config = matches[0]
    return project, config, ""


def record_delivery(
    db: Session,
    *,
    delivery_id: str,
    event_type: str,
    payload: dict[str, Any],
) -> tuple[WebhookDelivery, bool]:
    existing = (
        db.query(WebhookDelivery)
        .filter(WebhookDelivery.delivery_id == delivery_id)
        .first()
    )
    if existing is not None:
        return existing, True

    repository_data = payload.get("repository")
    repository = normalize_github_repository(
        repository_data.get("full_name")
        if isinstance(repository_data, dict)
        else None
    )
    branch = None
    commit_sha = None
    project = None
    status = "ignored"
    error_message = None

    if event_type != "push":
        error_message = f"Unsupported GitHub event: {event_type}"
    elif repository is None:
        error_message = "GitHub payload does not contain a valid repository"
    else:
        ref = payload.get("ref")
        if isinstance(ref, str) and ref.startswith("refs/heads/"):
            branch = ref.removeprefix("refs/heads/")
        if not branch:
            error_message = "Push ref is not a branch"
        elif payload.get("deleted"):
            error_message = "Deleted branch pushes do not start pipelines"
        else:
            try:
                commit_sha = validate_commit_sha(payload.get("after"))
            except ValueError as error:
                error_message = str(error)
            if commit_sha == "0" * 40:
                error_message = "Deleted branch pushes do not start pipelines"
            if not error_message:
                project, _, match_error = _match_project(db, repository, branch)
                if project is None:
                    error_message = match_error
                    if match_error.startswith("Multiple"):
                        status = "failed"
                else:
                    status = "queued"

    delivery = WebhookDelivery(
        delivery_id=delivery_id,
        event_type=event_type,
        repository=repository,
        branch=branch,
        commit_sha=commit_sha,
        project_id=project.id if project is not None else None,
        status=status,
        error_message=error_message,
        completed_at=datetime.utcnow() if status in {"ignored", "failed"} else None,
    )
    db.add(delivery)
    try:
        db.commit()
        db.refresh(delivery)
        return delivery, False
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(WebhookDelivery)
            .filter(WebhookDelivery.delivery_id == delivery_id)
            .first()
        )
        if existing is None:
            raise
        return existing, True


def recover_interrupted_deliveries(db: Session) -> int:
    deliveries = (
        db.query(WebhookDelivery)
        .filter(WebhookDelivery.status.in_(ACTIVE_DELIVERY_STATUSES))
        .all()
    )
    if not deliveries:
        return 0

    now = datetime.utcnow()
    for delivery in deliveries:
        delivery.status = "failed"
        delivery.completed_at = now
        delivery.error_message = (
            "Pipeline interrupted because the Mini-CICD server restarted"
        )
    db.commit()
    return len(deliveries)


def _error_text(error: Exception) -> str:
    if isinstance(error, HTTPException):
        return str(error.detail)
    text = str(error).strip()
    return text or error.__class__.__name__


def _mark_delivery_failed(delivery_id: int, error: Exception) -> None:
    with SessionLocal() as db:
        delivery = db.get(WebhookDelivery, delivery_id)
        if delivery is None or delivery.status in {"success", "build_succeeded"}:
            return
        delivery.status = "failed"
        delivery.completed_at = datetime.utcnow()
        delivery.error_message = _error_text(error)
        db.commit()


def _build_request(config: ProjectAutomationConfig) -> BuildStartRequest:
    return BuildStartRequest(
        project_id=config.project_id,
        build_type=config.build_type,
        build_script=config.build_script,
        docker_mode=config.docker_mode,
        image_name=config.image_name,
        image_tag=config.image_tag,
        dockerfile_path=config.dockerfile_path,
        build_context=config.build_context,
    )


def run_webhook_delivery(delivery_id: int) -> None:
    try:
        with SessionLocal() as db:
            delivery = db.get(WebhookDelivery, delivery_id)
            if delivery is None or delivery.status != "queued":
                return
            project = db.get(Project, delivery.project_id)
            config = (
                db.query(ProjectAutomationConfig)
                .filter(ProjectAutomationConfig.project_id == delivery.project_id)
                .first()
            )
            if project is None or project.status != "active":
                raise RuntimeError("Project is missing or inactive")
            if config is None or not config.enabled:
                raise RuntimeError("Project automation is no longer enabled")
            if (
                normalize_github_repository(project.repo_url)
                != delivery.repository
                or project.branch != delivery.branch
            ):
                raise RuntimeError(
                    "Project repository or branch changed after the webhook arrived"
                )

            delivery.status = "building"
            delivery.started_at = datetime.utcnow()
            delivery.error_message = None
            db.commit()

            runtime = get_execution_settings(db)
            build_service = BuildService(
                db=db,
                workspace_dir=runtime.workspace_dir,
                logs_dir=runtime.logs_dir,
                timeout_seconds=runtime.build_timeout_seconds,
                docker_enabled=runtime.docker_enabled,
            )
            build_response, build_execution = build_service.prepare_build(
                _build_request(config),
                commit_sha=delivery.commit_sha,
                request_source="GitHub webhook",
            )
            delivery.build_id = build_response.id
            db.commit()
            build_id = build_response.id
            build_execution_data = build_execution.model_dump()

        run_build_worker(build_id, build_execution_data)

        with SessionLocal() as db:
            delivery = db.get(WebhookDelivery, delivery_id)
            build = db.get(Build, build_id)
            if delivery is None or build is None:
                raise RuntimeError("Build result could not be loaded")
            if build.status != "success":
                raise RuntimeError(
                    f"Build #{build.id} failed: {build.error_message or 'unknown error'}"
                )
            if build.commit_hash != delivery.commit_sha:
                raise RuntimeError(
                    "Build commit does not match the GitHub webhook commit"
                )

            settings = get_settings(db)
            if not settings.auto_deploy_enabled:
                delivery.status = "build_succeeded"
                delivery.completed_at = datetime.utcnow()
                delivery.error_message = None
                db.commit()
                return

            project = db.get(Project, delivery.project_id)
            config = (
                db.query(ProjectAutomationConfig)
                .filter(ProjectAutomationConfig.project_id == delivery.project_id)
                .first()
            )
            target = get_deployment_target(db)
            if project is None or project.status != "active":
                raise RuntimeError("Project is missing or inactive before deploy")
            if config is None or not config.enabled:
                raise RuntimeError("Project automation was disabled before deploy")
            if target is None:
                raise RuntimeError("Deployment target is not configured")

            deploy_request = DeployStartRequest(
                build_id=build.id,
                server_ip=target.host,
                server_user=target.server_user,
                server_ssh_key=target.private_key_path,
                deploy_path=project.deploy_path,
                service_name=project.service_name,
                container_name=config.container_name,
                port_mapping=config.port_mapping,
                health_check_port=config.health_check_port,
                health_check_path=config.health_check_path,
            )
            runtime = get_execution_settings(db)
            deploy_service = DeployService(
                db=db,
                logs_dir=runtime.logs_dir,
                workspace_dir=runtime.workspace_dir,
                timeout_seconds=runtime.deploy_timeout_seconds,
                docker_enabled=runtime.docker_enabled,
                default_deploy_path=runtime.default_deploy_path,
                default_service_name=runtime.default_service_name,
            )
            deploy_response, deploy_execution = deploy_service.prepare_deploy(
                deploy_request,
                server_port=target.port,
                known_hosts_path=target.known_hosts_path,
            )
            delivery.deploy_id = deploy_response.id
            delivery.status = "deploying"
            db.commit()
            deploy_id = deploy_response.id
            deploy_execution_data = deploy_execution.model_dump()

        run_deploy_worker(deploy_id, deploy_execution_data)

        with SessionLocal() as db:
            delivery = db.get(WebhookDelivery, delivery_id)
            deploy = db.get(Deploy, deploy_id)
            if delivery is None or deploy is None:
                raise RuntimeError("Deploy result could not be loaded")
            if deploy.status != "success":
                raise RuntimeError(
                    f"Deploy #{deploy.id} failed: {deploy.error_message or 'unknown error'}"
                )
            delivery.status = "success"
            delivery.completed_at = datetime.utcnow()
            delivery.error_message = None
            db.commit()
    except Exception as error:
        _mark_delivery_failed(delivery_id, error)
