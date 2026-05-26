"""Health check and observability endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from motopay.alerts import AlertSeverity, alert_manager
from motopay.health import SystemHealthStatus, get_system_health
from motopay.interfaces.api.deps import require_metrics_or_admin

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=dict)
async def health_check() -> dict:
    """Basic health check for load balancers."""
    return {"status": "ok"}


@router.get("/status", response_model=SystemHealthStatus)
async def detailed_health() -> SystemHealthStatus:
    """Detailed system health status."""
    return await get_system_health()


@router.get("/metrics")
async def prometheus_metrics(_: object = Depends(require_metrics_or_admin)) -> Response:
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


alert_router = APIRouter(prefix="/alerts", tags=["alerts"])


@alert_router.get("", response_model=list[dict])
async def list_alerts(
    severity: str | None = None,
    tenant_id: int | None = None,
    limit: int = 100,
    _: object = Depends(require_metrics_or_admin),
) -> list[dict]:
    severity_enum = None
    if severity:
        try:
            severity_enum = AlertSeverity(severity)
        except ValueError:
            pass

    alerts = alert_manager.get_alerts(
        severity=severity_enum,
        tenant_id=tenant_id,
        limit=limit,
    )

    return [
        {
            "id": a.id,
            "timestamp": a.timestamp.isoformat(),
            "severity": a.severity.value,
            "title": a.title,
            "message": a.message,
            "tenant_id": a.tenant_id,
            "acknowledged": a.acknowledged,
        }
        for a in alerts
    ]


@alert_router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, _: object = Depends(require_metrics_or_admin)) -> dict:
    success = alert_manager.acknowledge(alert_id)
    return {"acknowledged": success}


@alert_router.get("/{alert_id}", response_model=dict | None)
async def get_alert(
    alert_id: str,
    _: object = Depends(require_metrics_or_admin),
) -> dict | None:
    alert = alert_manager.get_alert(alert_id)
    if not alert:
        return None

    return {
        "id": alert.id,
        "timestamp": alert.timestamp.isoformat(),
        "severity": alert.severity.value,
        "title": alert.title,
        "message": alert.message,
        "tenant_id": alert.tenant_id,
        "acknowledged": alert.acknowledged,
    }
