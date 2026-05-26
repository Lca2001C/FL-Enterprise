"""Operational endpoints for Celery observability."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from motopay.infrastructure.messaging.celery_observability import (
    dlq_discard,
    dlq_retry,
    get_celery_summary,
    get_dlq,
    health_check_celery,
)
from motopay.interfaces.api.deps import require_admin

router = APIRouter(prefix="/ops", tags=["ops"])


@router.get("/celery/summary")
def celery_summary(_: object = Depends(require_admin)) -> dict:
    return get_celery_summary()


@router.get("/celery/health")
def celery_health(_: object = Depends(require_admin)) -> dict:
    return health_check_celery()


@router.get("/dlq")
def list_dlq(_: object = Depends(require_admin)) -> dict:
    items = get_dlq()
    return {"items": items, "total": len(items)}


@router.post("/dlq/{task_id}/retry")
def retry_dlq_task(task_id: str, _: object = Depends(require_admin)) -> dict:
    ok = dlq_retry(task_id)
    return {"retried": ok}


@router.post("/dlq/{task_id}/discard")
def discard_dlq_task(task_id: str, _: object = Depends(require_admin)) -> dict:
    ok = dlq_discard(task_id)
    return {"discarded": ok}
