from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

import httpx
from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from motopay.config import get_settings
from motopay.infrastructure.db.models import Cobranca, Operacao
from motopay.infrastructure.db.session import get_db
from motopay.infrastructure.messaging.tasks import handle_domain_event
from motopay.infrastructure.payments.mercadopago_client import (
    MercadoPagoApiError,
    MercadoPagoClient,
    mp_token_for_operacao,
    mp_webhook_secret_for_operacao,
    verify_webhook_signature,
)
from motopay.infrastructure.payments.order_utils import is_order_paid, order_total_amount
from motopay.infrastructure.security.client_ip import get_client_ip
from motopay.infrastructure.security.rate_limit import (
    assert_webhook_not_blocked,
    clear_webhook_attempts,
    record_webhook_failure,
)
from motopay.services.billing_service import (
    handle_mercadopago_chargeback,
    handle_mercadopago_order_confirmed,
    handle_mercadopago_payment_confirmed,
    handle_mercadopago_preapproval_updated,
    handle_mercadopago_subscription_payment,
    sync_refund_from_mercadopago_payment,
)
from motopay.services.mercadopago_token_service import ensure_valid_mp_token

logger = logging.getLogger(__name__)

router = APIRouter(tags=["webhooks"])

_MP_CONFIRMED_STATUSES = frozenset({"approved", "authorized"})


def _resolve_operacao_for_webhook(db: Session, data_id: str) -> Operacao | None:
    cob = db.scalars(
        select(Cobranca).where(
            (Cobranca.mercadopago_order_id == data_id)
            | (Cobranca.mercadopago_payment_id == data_id)
        )
    ).first()
    if cob:
        return db.get(Operacao, cob.operacao_id)
    return None


def _verify_mp_signature(
    request: Request,
    *,
    data_id: str,
    op: Operacao | None,
) -> bool:
    secret = mp_webhook_secret_for_operacao(op)
    if not secret:
        secret = get_settings().mercadopago_webhook_secret.strip()
    if not secret:
        return True
    x_sig = request.headers.get("x-signature", "")
    x_req = request.headers.get("x-request-id", "")
    if not x_sig or not x_req:
        return False
    return verify_webhook_signature(
        secret=secret,
        x_signature=x_sig,
        x_request_id=x_req,
        data_id=data_id,
    )


def _mp_access_token(db: Session, op: Operacao | None) -> str:
    if op:
        token = ensure_valid_mp_token(db, op)
        if token:
            return token
    token = mp_token_for_operacao(op)
    if token:
        return token
    return get_settings().mercadopago_access_token.strip()


def _fetch_order(db: Session, op: Operacao | None, order_id: str) -> dict[str, Any]:
    return MercadoPagoClient(access_token=_mp_access_token(db, op)).get_order(order_id)


def _record_payment_status(db: Session, payment_id: str, status: str) -> None:
    cob = db.scalars(
        select(Cobranca).where(Cobranca.mercadopago_payment_id == payment_id)
    ).first()
    if cob:
        cob.mercadopago_payment_status = status
        db.add(cob)
        db.commit()


@router.post("/webhooks/mercadopago")
def mercadopago_webhook(
    request: Request,
    db: Session = Depends(get_db),
    body: dict[str, Any] = Body(...),
    data_id: str | None = Query(default=None, alias="data.id"),
) -> dict[str, bool]:
    ip = get_client_ip(request)
    assert_webhook_not_blocked(ip)

    topic = str(body.get("type") or body.get("action") or "").lower()
    data = body.get("data") or {}
    resource_id = str(data.get("id") or data_id or body.get("id") or "").strip()

    logger.info(
        "webhook_received topic=%s resource_id=%s ip=%s",
        topic,
        resource_id,
        ip,
    )

    if not resource_id:
        logger.warning("webhook_no_resource_id body_keys=%s", list(body.keys()))
        return {"ok": True}

    op = _resolve_operacao_for_webhook(db, resource_id)
    if not _verify_mp_signature(request, data_id=resource_id, op=op):
        logger.warning(
            "webhook_invalid_signature resource_id=%s ip=%s",
            resource_id,
            ip,
        )
        record_webhook_failure(ip)
        raise HTTPException(status_code=403, detail="Assinatura inválida")
    clear_webhook_attempts(ip)

    if "order" in topic:
        logger.info("webhook_order resource_id=%s", resource_id)
        try:
            order_data = _fetch_order(db, op, resource_id)
        except (httpx.HTTPError, MercadoPagoApiError) as exc:
            logger.error(
                "webhook_order_fetch_failed resource_id=%s error=%s",
                resource_id,
                exc,
            )
            raise HTTPException(status_code=502, detail="Falha ao validar order no MP") from exc
        if not is_order_paid(order_data):
            logger.info(
                "webhook_order_not_paid resource_id=%s status=%s",
                resource_id,
                order_data.get("status"),
            )
            return {"ok": True}
        amount = order_total_amount(order_data)
        _found, ev_id = handle_mercadopago_order_confirmed(
            db,
            mercadopago_order_id=resource_id,
            order_data=order_data,
            value=amount,
        )
        logger.info(
            "webhook_order_confirmed resource_id=%s found=%s ev_id=%s",
            resource_id,
            _found,
            ev_id,
        )
        if ev_id:
            handle_domain_event.delay(ev_id)
        return {"ok": True}

    if "preapproval" in topic or "subscription_preapproval" in topic:
        logger.info("webhook_preapproval resource_id=%s", resource_id)
        try:
            pre_data = MercadoPagoClient(
                access_token=_mp_access_token(db, op)
            ).get_preapproval(resource_id)
        except (httpx.HTTPError, MercadoPagoApiError) as exc:
            logger.error(
                "webhook_preapproval_fetch_failed resource_id=%s error=%s",
                resource_id,
                exc,
            )
            raise HTTPException(status_code=502, detail="Falha ao validar assinatura no MP") from exc
        handle_mercadopago_preapproval_updated(
            db, preapproval_id=resource_id, preapproval_data=pre_data
        )
        logger.info("webhook_preapproval_updated resource_id=%s", resource_id)
        return {"ok": True}

    if "chargeback" in topic:
        logger.info("webhook_chargeback resource_id=%s", resource_id)
        try:
            cb_data = MercadoPagoClient(
                access_token=_mp_access_token(db, op)
            ).get_chargeback(resource_id)
        except (httpx.HTTPError, MercadoPagoApiError) as exc:
            logger.error(
                "webhook_chargeback_fetch_failed resource_id=%s error=%s",
                resource_id,
                exc,
            )
            raise HTTPException(status_code=502, detail="Falha ao validar chargeback no MP") from exc
        _found, ev_id = handle_mercadopago_chargeback(db, chargeback_data=cb_data)
        logger.info(
            "webhook_chargeback_processed resource_id=%s found=%s ev_id=%s",
            resource_id,
            _found,
            ev_id,
        )
        if ev_id:
            handle_domain_event.delay(ev_id)
        return {"ok": True}

    if "payment" in topic:
        logger.info("webhook_payment resource_id=%s", resource_id)
        try:
            pay_data = MercadoPagoClient(
                access_token=_mp_access_token(db, op)
            ).get_payment(resource_id)
        except (httpx.HTTPError, MercadoPagoApiError) as exc:
            logger.error(
                "webhook_payment_fetch_failed resource_id=%s error=%s",
                resource_id,
                exc,
            )
            raise HTTPException(status_code=502, detail="Falha ao validar pagamento no MP") from exc
        status = str(pay_data.get("status", "")).lower()
        logger.info("webhook_payment_status resource_id=%s status=%s", resource_id, status)
        _record_payment_status(db, resource_id, status)
        if status in ("refunded", "partially_refunded"):
            _found, ev_id = sync_refund_from_mercadopago_payment(db, pay_data=pay_data)
            logger.info(
                "webhook_refund_processed resource_id=%s found=%s ev_id=%s",
                resource_id,
                _found,
                ev_id,
            )
            if ev_id:
                handle_domain_event.delay(ev_id)
            return {"ok": True}
        if status in ("rejected", "cancelled"):
            logger.info("webhook_payment_terminal resource_id=%s status=%s", resource_id, status)
            return {"ok": True}
        if status not in _MP_CONFIRMED_STATUSES:
            logger.info("webhook_payment_pending resource_id=%s status=%s", resource_id, status)
            return {"ok": True}
        raw_val = pay_data.get("transaction_amount")
        val = Decimal(str(raw_val)) if raw_val is not None else None
        if pay_data.get("preapproval_id"):
            _found, ev_id = handle_mercadopago_subscription_payment(
                db,
                mercadopago_payment_id=resource_id,
                pay_data=pay_data,
                value=val,
            )
            logger.info(
                "webhook_subscription_payment resource_id=%s found=%s ev_id=%s",
                resource_id,
                _found,
                ev_id,
            )
        else:
            _found, ev_id = handle_mercadopago_payment_confirmed(
                db, mercadopago_payment_id=resource_id, value=val
            )
            logger.info(
                "webhook_payment_confirmed resource_id=%s found=%s ev_id=%s",
                resource_id,
                _found,
                ev_id,
            )
        if ev_id:
            handle_domain_event.delay(ev_id)

    logger.info("webhook_done topic=%s resource_id=%s", topic, resource_id)
    return {"ok": True}
