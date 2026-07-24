from unittest.mock import patch

from backend.build.models import Build
from backend.common.database import SessionLocal
from backend.deploy.models import Deploy
from backend.project.models import Project
from backend.settings.service import get_settings
from backend.webhook.models import (
    DeploymentTargetSettings,
    ProjectAutomationConfig,
    WebhookDelivery,
)
from backend.webhook.service import run_webhook_delivery


COMMIT_SHA = "b" * 40


def seed_delivery(runtime_root, *, auto_deploy: bool) -> int:
    with SessionLocal() as db:
        settings = get_settings(db)
        settings.workspace_dir = str(runtime_root / "workspace")
        settings.logs_dir = str(runtime_root / "logs")
        settings.auto_deploy_enabled = auto_deploy
        settings.docker_enabled = True

        project = Project(
            name="worker-demo",
            repo_url="https://github.com/Holizing/Mini-CICD.git",
            branch="main",
            deploy_path="/srv/worker-demo",
            service_name="nginx",
            status="active",
        )
        db.add(project)
        db.commit()
        db.refresh(project)

        db.add(
            ProjectAutomationConfig(
                project_id=project.id,
                enabled=True,
                build_type="source",
                build_script="npm ci\nnpm run build",
                health_check_port=8081,
                health_check_path="/",
            )
        )
        if auto_deploy:
            db.add(
                DeploymentTargetSettings(
                    host="127.0.0.1",
                    port=22,
                    server_user="deploy",
                    private_key_path="/tmp/test-deploy-key",
                    known_hosts_path="/tmp/test-known-hosts",
                )
            )

        delivery = WebhookDelivery(
            delivery_id=f"worker-{int(auto_deploy)}",
            event_type="push",
            repository="holizing/mini-cicd",
            branch="main",
            commit_sha=COMMIT_SHA,
            project_id=project.id,
            status="queued",
        )
        db.add(delivery)
        db.commit()
        db.refresh(delivery)
        return delivery.id


def complete_build(runtime_root):
    def worker(build_id: int, execution_data: dict) -> None:
        with SessionLocal() as db:
            build = db.get(Build, build_id)
            build.status = "success"
            build.commit_hash = execution_data["commit_sha"]
            build.artifact_path = str(runtime_root / "artifact")
            build.artifact_type = "directory"
            build.detected_framework = "React"
            build.detected_runtime = "Node.js"
            build.detected_build_tool = "npm"
            build.detected_packaging = "static"
            build.recommended_deploy_path = "/srv/worker-demo"
            build.recommended_service_name = "nginx"
            db.commit()

    return worker


def fail_build(build_id: int, execution_data: dict) -> None:
    del execution_data
    with SessionLocal() as db:
        build = db.get(Build, build_id)
        build.status = "failed"
        build.error_message = "simulated build failure"
        db.commit()


def complete_deploy(deploy_id: int, execution_data: dict) -> None:
    del execution_data
    with SessionLocal() as db:
        deploy = db.get(Deploy, deploy_id)
        deploy.status = "success"
        db.commit()


def test_worker_stops_after_successful_build_when_auto_deploy_is_off(
    clean_database,
):
    delivery_id = seed_delivery(clean_database, auto_deploy=False)

    with patch(
        "backend.webhook.service.run_build_worker",
        side_effect=complete_build(clean_database),
    ):
        run_webhook_delivery(delivery_id)

    with SessionLocal() as db:
        delivery = db.get(WebhookDelivery, delivery_id)
        build = db.get(Build, delivery.build_id)
        assert delivery.status == "build_succeeded"
        assert delivery.deploy_id is None
        assert delivery.completed_at is not None
        assert build.status == "success"
        assert build.commit_hash == COMMIT_SHA
        assert db.query(Deploy).count() == 0


def test_worker_runs_build_then_deploy_when_auto_deploy_is_on(clean_database):
    delivery_id = seed_delivery(clean_database, auto_deploy=True)

    with (
        patch(
            "backend.webhook.service.run_build_worker",
            side_effect=complete_build(clean_database),
        ),
        patch(
            "backend.webhook.service.run_deploy_worker",
            side_effect=complete_deploy,
        ),
    ):
        run_webhook_delivery(delivery_id)

    with SessionLocal() as db:
        delivery = db.get(WebhookDelivery, delivery_id)
        build = db.get(Build, delivery.build_id)
        deploy = db.get(Deploy, delivery.deploy_id)
        assert delivery.status == "success"
        assert delivery.completed_at is not None
        assert build.commit_hash == COMMIT_SHA
        assert deploy.status == "success"
        assert deploy.build_id == build.id
        assert deploy.project_id == delivery.project_id
        assert deploy.server_ip == "127.0.0.1"


def test_worker_records_build_failure_and_does_not_deploy(clean_database):
    delivery_id = seed_delivery(clean_database, auto_deploy=True)

    with (
        patch(
            "backend.webhook.service.run_build_worker",
            side_effect=fail_build,
        ),
        patch("backend.webhook.service.run_deploy_worker") as deploy_worker,
    ):
        run_webhook_delivery(delivery_id)

    with SessionLocal() as db:
        delivery = db.get(WebhookDelivery, delivery_id)
        assert delivery.status == "failed"
        assert delivery.completed_at is not None
        assert "simulated build failure" in delivery.error_message
        assert delivery.deploy_id is None
        assert db.query(Deploy).count() == 0
    deploy_worker.assert_not_called()


def test_worker_rejects_a_build_from_the_wrong_commit(clean_database):
    delivery_id = seed_delivery(clean_database, auto_deploy=False)

    def complete_wrong_commit(build_id: int, execution_data: dict) -> None:
        del execution_data
        with SessionLocal() as db:
            build = db.get(Build, build_id)
            build.status = "success"
            build.commit_hash = "c" * 40
            db.commit()

    with patch(
        "backend.webhook.service.run_build_worker",
        side_effect=complete_wrong_commit,
    ):
        run_webhook_delivery(delivery_id)

    with SessionLocal() as db:
        delivery = db.get(WebhookDelivery, delivery_id)
        assert delivery.status == "failed"
        assert "does not match" in delivery.error_message
