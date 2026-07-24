import hashlib
import hmac
import json
from datetime import datetime
from unittest.mock import patch

from backend.common.database import SessionLocal
from backend.project.models import Project
from backend.settings.models import SystemSettings
from backend.settings.service import get_settings
from backend.webhook.models import ProjectAutomationConfig, WebhookDelivery
from backend.webhook.service import recover_interrupted_deliveries


WEBHOOK_SECRET = "webhook-test-secret-with-at-least-32-characters"
COMMIT_SHA = "a" * 40


def webhook_payload(branch: str = "main") -> dict:
    return {
        "ref": f"refs/heads/{branch}",
        "after": COMMIT_SHA,
        "deleted": False,
        "repository": {"full_name": "Holizing/Mini-CICD"},
    }


def signed_headers(
    body: bytes,
    *,
    delivery_id: str = "delivery-1",
    event: str = "push",
    secret: str = WEBHOOK_SECRET,
) -> dict[str, str]:
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return {
        "Content-Type": "application/json",
        "X-GitHub-Event": event,
        "X-GitHub-Delivery": delivery_id,
        "X-Hub-Signature-256": f"sha256={digest}",
    }


def encode_payload(payload: dict) -> bytes:
    return json.dumps(payload, separators=(",", ":")).encode()


def configure_secret(secret: str = WEBHOOK_SECRET) -> None:
    with SessionLocal() as db:
        settings = get_settings(db)
        settings.webhook_secret = secret
        db.commit()


def configure_automated_project() -> int:
    with SessionLocal() as db:
        project = Project(
            name="webhook-demo",
            repo_url="https://github.com/Holizing/Mini-CICD.git",
            branch="main",
            deploy_path="/srv/mini-cicd-demo",
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
                health_check_path="/",
            )
        )
        db.commit()
        return project.id


def test_webhook_requires_configured_secret(api_client):
    body = encode_payload(webhook_payload())

    response = api_client.post(
        "/webhooks/github",
        content=body,
        headers=signed_headers(body),
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "GitHub webhook secret is not configured"


def test_webhook_rejects_invalid_signature(api_client):
    configure_secret()
    body = encode_payload(webhook_payload())
    headers = signed_headers(body)
    headers["X-Hub-Signature-256"] = "sha256=" + ("0" * 64)

    response = api_client.post("/webhooks/github", content=body, headers=headers)

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid GitHub webhook signature"


def test_ping_is_acknowledged_without_recording_delivery(api_client):
    configure_secret()
    body = encode_payload({"zen": "Keep it logically awesome."})

    response = api_client.post(
        "/webhooks/github",
        content=body,
        headers=signed_headers(body, event="ping"),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ignored"
    with SessionLocal() as db:
        assert db.query(WebhookDelivery).count() == 0


def test_push_is_idempotent_and_schedules_one_pipeline(api_client):
    configure_secret()
    project_id = configure_automated_project()
    body = encode_payload(webhook_payload())
    headers = signed_headers(body)

    with patch("backend.webhook.service.run_webhook_delivery") as worker:
        first = api_client.post("/webhooks/github", content=body, headers=headers)
        second = api_client.post("/webhooks/github", content=body, headers=headers)

    assert first.status_code == 202
    assert first.json()["status"] == "queued"
    assert first.json()["duplicate"] is False
    assert second.status_code == 202
    assert second.json()["duplicate"] is True
    worker.assert_called_once()

    with SessionLocal() as db:
        deliveries = db.query(WebhookDelivery).all()
        assert len(deliveries) == 1
        assert deliveries[0].project_id == project_id
        assert deliveries[0].commit_sha == COMMIT_SHA


def test_wrong_branch_is_recorded_as_ignored(api_client):
    configure_secret()
    configure_automated_project()
    body = encode_payload(webhook_payload(branch="feature/not-main"))

    with patch("backend.webhook.service.run_webhook_delivery") as worker:
        response = api_client.post(
            "/webhooks/github",
            content=body,
            headers=signed_headers(body, delivery_id="wrong-branch"),
        )

    assert response.status_code == 202
    assert response.json()["status"] == "ignored"
    assert "branch" in response.json()["message"].lower()
    worker.assert_not_called()


def test_webhook_rejects_oversized_and_malformed_bodies(api_client):
    configure_secret()
    oversized_body = b"x" * ((1024 * 1024) + 1)
    oversized = api_client.post(
        "/webhooks/github",
        content=oversized_body,
        headers=signed_headers(oversized_body, delivery_id="oversized"),
    )

    malformed_body = b"{not-json"
    malformed = api_client.post(
        "/webhooks/github",
        content=malformed_body,
        headers=signed_headers(malformed_body, delivery_id="malformed"),
    )

    assert oversized.status_code == 413
    assert malformed.status_code == 400


def test_delivery_endpoints_require_authentication(unauthenticated_client):
    response = unauthenticated_client.get("/webhooks/deliveries")

    assert response.status_code == 401


def test_settings_validate_and_mask_webhook_secret(api_client):
    configure_secret()

    short_secret = api_client.put(
        "/settings",
        json={"webhook_secret": "too-short"},
    )
    blank_secret = api_client.put(
        "/settings",
        json={"webhook_secret": "   "},
    )
    replacement = "replacement-webhook-secret-at-least-32-characters"
    updated = api_client.put(
        "/settings",
        json={"webhook_secret": replacement},
    )

    assert short_secret.status_code == 422
    assert "at least 32 characters" in str(short_secret.json())
    assert blank_secret.status_code == 200
    assert blank_secret.json()["webhook_secret_configured"] is True
    assert "webhook_secret" not in blank_secret.json()
    assert updated.status_code == 200
    assert "webhook_secret" not in updated.json()

    with SessionLocal() as db:
        settings = db.query(SystemSettings).one()
        assert settings.webhook_secret == replacement


def test_recovery_marks_interrupted_deliveries_failed(clean_database):
    with SessionLocal() as db:
        db.add_all(
            [
                WebhookDelivery(
                    delivery_id=f"interrupted-{status}",
                    event_type="push",
                    status=status,
                )
                for status in ("queued", "building", "deploying")
            ]
        )
        db.add(
            WebhookDelivery(
                delivery_id="already-complete",
                event_type="push",
                status="success",
                completed_at=datetime.utcnow(),
            )
        )
        db.commit()

        assert recover_interrupted_deliveries(db) == 3

        interrupted = (
            db.query(WebhookDelivery)
            .filter(WebhookDelivery.delivery_id.like("interrupted-%"))
            .all()
        )
        completed = (
            db.query(WebhookDelivery)
            .filter(WebhookDelivery.delivery_id == "already-complete")
            .one()
        )

    assert {delivery.status for delivery in interrupted} == {"failed"}
    assert all(delivery.completed_at is not None for delivery in interrupted)
    assert completed.status == "success"
