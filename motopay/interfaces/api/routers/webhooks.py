from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from motopay.config import get_settings
from motopay.infrastructure.db.session import get_db
from motopay.infrastructure.messaging.tasks import handle_domain_event
from motopay.services.billing_service import handle_payment_confirmed

router = APIRouter(tags=["webhooks"])

_PAYMENT_EVENTS = frozenset(
    {
        "PAYMENT_RECEIVED",
        "PAYMENT_CONFIRMED",
        "PAYMENT_RECEIVED_IN_ACCOUNT",
    }
)


@router.post("/webhooks/asaas")
def asaas_webhook(
    db: Session = Depends(get_db),
    token: str = Query(..., description="Igual a ASAAS_WEBHOOK_TOKEN"),
    body: dict[str, Any] = Body(...),
) -> dict[str, bool]:
    if token != get_settings().asaas_webhook_token:
        raise HTTPException(status_code=403, detail="Token inválido")
    event = body.get("event") or body.get("type")
    payment = body.get("payment") or {}
    pid = payment.get("id")
    if event in _PAYMENT_EVENTS and pid:
        raw_val = payment.get("value")
        val = Decimal(str(raw_val)) if raw_val is not None else None
        _found, ev_id = handle_payment_confirmed(db, asaas_payment_id=str(pid), value=val)
        if ev_id:
            handle_domain_event.delay(ev_id)
    return {"ok": True}
