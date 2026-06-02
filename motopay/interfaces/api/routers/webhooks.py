from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from motopay.config.mercadopago_credentials import effective_mercadopago_webhook_secret
from motopay.infrastructure.db.models import Cobranca, Operacao
from motopay.infrastructure.db.session import get_db
from motopay.infrastructure.messaging.tasks import handle_domain_event
from motopay.infrastructure.payments.mercadopago_client import (
    MercadoPagoClient,
    is_order_paid,
    mp_token_for_operacao,
    mp_webhook_secret_for_operacao,
    normalize_webhook_data_id,
    order_total_amount,
    verify_webhook_signature,
)
from motopay.infrastructure.payments.mercadopago_sdk import MercadoPagoApiError
from motopay.infrastructure.security.client_ip import get_client_ip
from motopay.infrastructure.security.rate_limit import (
    assert_webhook_not_blocked,
    clear_webhook_attempts,
    record_webhook_failure,
)
from motopay.services.billing_service import handle_mercadopago_order_confirmed

router = APIRouter(tags=["webhooks"])


def _resolve_operacao_for_order(db: Session, order_id: str) -> Operacao | None:
    if not order_id.strip():
        return None
    cob = db.scalars(
        select(Cobranca).where(Cobranca.mercadopago_order_id == order_id)
    ).first()
    if not cob:
        return None
    return db.get(Operacao, cob.operacao_id)


def _order_confirmed_in_mercadopago(
    order_id: str, *, op: Operacao | None
) -> tuple[bool, Decimal | None]:
    token = mp_token_for_operacao(op)
    if not token:
        return True, None
    try:
        data = MercadoPagoClient(access_token=token).get_order(order_id)
    except MercadoPagoApiError as exc:
        raise HTTPException(
            status_code=502,
            detail="Falha ao validar order no Mercado Pago",
        ) from exc
    if not is_order_paid(data):
        return False, None
    return True, order_total_amount(data)


def _extract_webhook_data_id(body: dict[str, Any], request: Request) -> str | None:
    data = body.get("data") or {}
    pid = data.get("id") or body.get("id")
    if pid is not None:
        return str(pid)
    query_id = request.query_params.get("data.id")
    if query_id:
        return str(query_id)
    return None


def _is_order_webhook(body: dict[str, Any], request: Request) -> bool:
    topic = str(body.get("type") or body.get("action") or request.query_params.get("type") or "")
    topic_lower = topic.lower()
    if body.get("entity") == "order":
        return True
    if topic_lower == "order" or topic_lower.startswith("order."):
        return True
    return False


def _verify_mercadopago_webhook(
    request: Request,
    *,
    data_id: str,
    op: Operacao | None,
) -> None:
    secret = mp_webhook_secret_for_operacao(op)
    if not secret:
        secret = effective_mercadopago_webhook_secret()
    if not secret:
        return
    manifest_id = normalize_webhook_data_id(data_id)
    if not verify_webhook_signature(
        secret=secret,
        x_signature=request.headers.get("x-signature", ""),
        x_request_id=request.headers.get("x-request-id", ""),
        data_id=manifest_id,
    ):
        raise HTTPException(status_code=403, detail="Assinatura inválida")


@router.post("/webhooks/mercadopago")
def mercadopago_webhook(
    request: Request,
    db: Session = Depends(get_db),
    body: dict[str, Any] = Body(...),
) -> dict[str, bool]:
    ip = get_client_ip(request)
    assert_webhook_not_blocked(ip)

    data_id = _extract_webhook_data_id(body, request) or ""
    op = _resolve_operacao_for_order(db, data_id) if data_id else None

    try:
        _verify_mercadopago_webhook(request, data_id=data_id, op=op)
    except HTTPException:
        record_webhook_failure(ip)
        raise

    clear_webhook_attempts(ip)

    if not data_id or not _is_order_webhook(body, request):
        return {"ok": True}

    ok, val = _order_confirmed_in_mercadopago(data_id, op=op)
    if not ok:
        return {"ok": True}
    _found, ev_id = handle_mercadopago_order_confirmed(
        db, mercadopago_order_id=data_id, value=val
    )
    if ev_id:
        handle_domain_event.delay(ev_id)
    return {"ok": True}
