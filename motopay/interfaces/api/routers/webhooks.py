from __future__ import annotations

from decimal import Decimal
from typing import Any

import httpx
from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from motopay.config import get_settings
from motopay.infrastructure.db.session import get_db
from motopay.infrastructure.messaging.tasks import handle_domain_event
from motopay.infrastructure.payments.asaas_client import AsaasClient
from motopay.infrastructure.security.client_ip import get_client_ip
from motopay.infrastructure.security.rate_limit import (
    assert_webhook_not_blocked,
    clear_webhook_attempts,
    record_webhook_failure,
)
from motopay.infrastructure.security.webhook_auth import (
    extract_webhook_token,
    verify_webhook_token,
    webhook_rejects_query_token,
)
from motopay.services.billing_service import (
    handle_mercadopago_payment_confirmed,
    handle_payment_confirmed,
)

router = APIRouter(tags=["webhooks"])

_PAYMENT_EVENTS = frozenset(
    {
        "PAYMENT_RECEIVED",
        "PAYMENT_CONFIRMED",
        "PAYMENT_RECEIVED_IN_ACCOUNT",
    }
)

_ASAAS_CONFIRMED_STATUSES = frozenset(
    {
        "RECEIVED",
        "CONFIRMED",
        "RECEIVED_IN_CASH",
        "DUNNING_RECEIVED",
    }
)


def _payment_confirmed_in_asaas(payment_id: str) -> bool:
    settings = get_settings()
    if not settings.asaas_webhook_verify_with_api or not settings.asaas_api_key.strip():
        return True
    try:
        data = AsaasClient().get_payment(payment_id)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail="Falha ao validar pagamento na Asaas",
        ) from exc
    status = str(data.get("status", "")).upper()
    return status in _ASAAS_CONFIRMED_STATUSES


@router.post("/webhooks/asaas")
def asaas_webhook(
    request: Request,
    db: Session = Depends(get_db),
    token: str | None = Query(default=None, description="Legado Asaas: token na URL"),
    body: dict[str, Any] = Body(...),
) -> dict[str, bool]:
    ip = get_client_ip(request)
    assert_webhook_not_blocked(ip)

    settings = get_settings()
    expected = settings.asaas_webhook_token
    if not expected.strip():
        raise HTTPException(status_code=503, detail="Webhook não configurado")

    if webhook_rejects_query_token(
        query_token=token,
        headers=request.headers,
        allow_query=settings.allow_webhook_token_in_query,
    ):
        record_webhook_failure(ip)
        raise HTTPException(
            status_code=403,
            detail="Em produção use o header X-Webhook-Token (token na URL não é permitido).",
        )

    provided = extract_webhook_token(query_token=token, headers=request.headers)
    if not verify_webhook_token(provided, expected):
        record_webhook_failure(ip)
        raise HTTPException(status_code=403, detail="Token inválido")

    clear_webhook_attempts(ip)

    event = body.get("event") or body.get("type")
    payment = body.get("payment") or {}
    pid = payment.get("id")
    if event in _PAYMENT_EVENTS and pid:
        if not _payment_confirmed_in_asaas(str(pid)):
            return {"ok": True}
        raw_val = payment.get("value")
        val = Decimal(str(raw_val)) if raw_val is not None else None
        _found, ev_id = handle_payment_confirmed(db, asaas_payment_id=str(pid), value=val)
        if ev_id:
            handle_domain_event.delay(ev_id)
    return {"ok": True}


_MP_CONFIRMED_STATUSES = frozenset({"approved", "authorized"})


def _payment_confirmed_in_mercadopago(payment_id: str) -> tuple[bool, Decimal | None]:
    settings = get_settings()
    if not settings.mercadopago_access_token.strip():
        return True, None
    try:
        from motopay.infrastructure.payments.mercadopago_client import MercadoPagoClient

        data = MercadoPagoClient().get_payment(payment_id)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail="Falha ao validar pagamento no Mercado Pago",
        ) from exc
    status = str(data.get("status", "")).lower()
    raw_val = data.get("transaction_amount")
    val = Decimal(str(raw_val)) if raw_val is not None else None
    return status in _MP_CONFIRMED_STATUSES, val


@router.post("/webhooks/mercadopago")
def mercadopago_webhook(
    request: Request,
    db: Session = Depends(get_db),
    body: dict[str, Any] = Body(...),
) -> dict[str, bool]:
    ip = get_client_ip(request)
    assert_webhook_not_blocked(ip)

    secret = get_settings().mercadopago_webhook_secret.strip()
    if secret:
        sig = request.headers.get("x-signature", "")
        if secret not in sig and sig != secret:
            record_webhook_failure(ip)
            raise HTTPException(status_code=403, detail="Assinatura inválida")

    clear_webhook_attempts(ip)

    topic = body.get("type") or body.get("action") or ""
    data = body.get("data") or {}
    pid = data.get("id") or body.get("id")
    if pid and ("payment" in str(topic).lower() or body.get("entity") == "payment"):
        ok, val = _payment_confirmed_in_mercadopago(str(pid))
        if not ok:
            return {"ok": True}
        _found, ev_id = handle_mercadopago_payment_confirmed(
            db, mercadopago_payment_id=str(pid), value=val
        )
        if ev_id:
            handle_domain_event.delay(ev_id)
    return {"ok": True}
