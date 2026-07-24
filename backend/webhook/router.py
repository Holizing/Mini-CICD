import json
from typing import Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Header,
    HTTPException,
    Query,
    Request,
    status,
)
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from backend.common.database import get_db
from backend.settings.service import get_settings
from backend.webhook import service
from backend.webhook.schemas import (
    DeliveryStatus,
    DeploymentTargetResponse,
    DeploymentTargetTestResponse,
    DeploymentTargetUpdate,
    ProjectAutomationResponse,
    ProjectAutomationUpdate,
    WebhookAcceptedResponse,
    WebhookDeliveryListResponse,
    WebhookDeliveryResponse,
)


MAX_WEBHOOK_BODY_BYTES = 1024 * 1024

public_router = APIRouter(prefix="/webhooks", tags=["webhooks"])
protected_router = APIRouter(tags=["automation"])


async def read_limited_body(request: Request) -> bytes:
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > MAX_WEBHOOK_BODY_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Webhook payload exceeds 1 MiB",
            )
        body.extend(chunk)
    return bytes(body)


@public_router.post(
    "/github",
    response_model=WebhookAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def receive_github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    github_event: str = Header(
        alias="X-GitHub-Event",
        min_length=1,
        max_length=100,
    ),
    github_delivery: str = Header(
        alias="X-GitHub-Delivery",
        min_length=1,
        max_length=255,
    ),
    github_signature: Optional[str] = Header(
        default=None,
        alias="X-Hub-Signature-256",
        max_length=128,
    ),
    db: Session = Depends(get_db),
):
    body = await read_limited_body(request)
    settings = get_settings(db)
    if not settings.webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub webhook secret is not configured",
        )
    if not service.verify_github_signature(
        settings.webhook_secret,
        body,
        github_signature or "",
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid GitHub webhook signature",
        )

    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook body must be valid UTF-8 JSON",
        ) from None
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook JSON root must be an object",
        )

    if github_event == "ping":
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "delivery_id": github_delivery,
                "status": "ignored",
                "duplicate": False,
                "message": "GitHub webhook ping accepted",
            },
        )

    delivery, duplicate = service.record_delivery(
        db,
        delivery_id=github_delivery,
        event_type=github_event,
        payload=payload,
    )
    if delivery.status == "queued" and not duplicate:
        background_tasks.add_task(service.run_webhook_delivery, delivery.id)

    return WebhookAcceptedResponse(
        delivery_id=delivery.delivery_id,
        status=delivery.status,
        duplicate=duplicate,
        message=(
            "Delivery already recorded"
            if duplicate
            else delivery.error_message or "Pipeline queued"
        ),
    )


@protected_router.get(
    "/webhooks/deliveries",
    response_model=WebhookDeliveryListResponse,
)
async def list_webhook_deliveries(
    delivery_status: Optional[DeliveryStatus] = Query(default=None, alias="status"),
    project_id: Optional[int] = Query(default=None, gt=0),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    deliveries, total = service.get_deliveries(
        db,
        status=delivery_status,
        project_id=project_id,
        limit=limit,
        offset=offset,
    )
    return WebhookDeliveryListResponse(deliveries=deliveries, total=total)


@protected_router.get(
    "/webhooks/deliveries/{delivery_id}",
    response_model=WebhookDeliveryResponse,
)
async def read_webhook_delivery(
    delivery_id: int,
    db: Session = Depends(get_db),
):
    delivery = service.get_delivery(db, delivery_id)
    if delivery is None:
        raise HTTPException(status_code=404, detail="Webhook delivery not found")
    return delivery


@protected_router.get(
    "/settings/deployment-target",
    response_model=DeploymentTargetResponse,
)
async def read_deployment_target(db: Session = Depends(get_db)):
    return service.deployment_target_response(service.get_deployment_target(db))


@protected_router.put(
    "/settings/deployment-target",
    response_model=DeploymentTargetResponse,
)
async def save_deployment_target(
    request: DeploymentTargetUpdate,
    db: Session = Depends(get_db),
):
    return service.update_deployment_target(db, request)


@protected_router.post(
    "/settings/deployment-target/test",
    response_model=DeploymentTargetTestResponse,
)
def check_deployment_target(db: Session = Depends(get_db)):
    return service.test_deployment_target(db)


@protected_router.get(
    "/projects/{project_id}/automation",
    response_model=ProjectAutomationResponse,
)
async def read_project_automation(
    project_id: int,
    db: Session = Depends(get_db),
):
    return service.get_project_automation(db, project_id)


@protected_router.put(
    "/projects/{project_id}/automation",
    response_model=ProjectAutomationResponse,
)
async def save_project_automation(
    project_id: int,
    request: ProjectAutomationUpdate,
    db: Session = Depends(get_db),
):
    return service.update_project_automation(db, project_id, request)
