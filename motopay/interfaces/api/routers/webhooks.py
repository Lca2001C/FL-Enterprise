from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

<<<<<<< HEAD
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
=======
import httpx
from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from motopay.config import get_settings
from motopay.infrastructure.db.models import Cobranca, Operacao
from motopay.infrastructure.db.session import get_db
from motopay.infrastructure.messaging.dispatch import enqueue_domain_event
from motopay.infrastructure.payments.mercadopago_client import (
    MercadoPagoApiError,
    MercadoPagoClient,
    mp_operacao_ready_for_payments,
    mp_webhook_secret_for_operacao,
    require_operacao_mp_token,
    verify_webhook_signature,
)
from motopay.infrastructure.payments.order_utils import is_order_paid, order_total_amount
>>>>>>> main
from motopay.infrastructure.security.client_ip import get_client_ip
from motopay.infrastructure.security.rate_limit import (
    assert_webhook_not_blocked,
    clear_webhook_attempts,
    record_webhook_failure,
)
<<<<<<< HEAD
from motopay.services.billing_service import handle_mercadopago_order_confirmed
=======
from motopay.services.billing_service import (
    handle_mercadopago_chargeback,
    handle_mercadopago_order_confirmed,
    handle_mercadopago_payment_confirmed,
    handle_mercadopago_preapproval_updated,
    handle_mercadopago_subscription_payment,
    sync_refund_from_mercadopago_payment,
)

logger = logging.getLogger(__name__)
>>>>>>> main

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


<<<<<<< HEAD
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
=======
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
>>>>>>> main
    request: Request,
    *,
    data_id: str,
    op: Operacao | None,
<<<<<<< HEAD
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
=======
) -> bool:
    secret = mp_webhook_secret_for_operacao(op)
    if not secret:
        secret = get_settings().mercadopago_webhook_secret.strip()
    if not secret:
        # Sem secret configurado: em produção rejeita (fail-closed) — aceitar
        # webhook não assinado permitiria forjar notificações de pagamento.
        if get_settings().environment == "production":
            logger.error(
                "webhook_secret_missing: configure MERCADOPAGO_WEBHOOK_SECRET "
                "(ou o secret da operação) — webhook rejeitado em produção."
            )
            return False
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
    if op and mp_operacao_ready_for_payments(op):
        return require_operacao_mp_token(db, op)
    settings = get_settings()
    if settings.is_production:
        return ""
    return settings.mercadopago_access_token.strip()


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
>>>>>>> main


@router.post("/webhooks/mercadopago")
def mercadopago_webhook(
    request: Request,
    db: Session = Depends(get_db),
    body: dict[str, Any] = Body(...),
    data_id: str | None = Query(default=None, alias="data.id"),
) -> dict[str, bool]:
    ip = get_client_ip(request)
    assert_webhook_not_blocked(ip)

<<<<<<< HEAD
    data_id = _extract_webhook_data_id(body, request) or ""
    op = _resolve_operacao_for_order(db, data_id) if data_id else None

    try:
        _verify_mercadopago_webhook(request, data_id=data_id, op=op)
    except HTTPException:
        record_webhook_failure(ip)
        raise
=======
    topic = str(body.get("type") or body.get("action") or "").lower()
    data = body.get("data") or {}
    resource_id = str(data.get("id") or data_id or body.get("id") or "").strip()
>>>>>>> main

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

<<<<<<< HEAD
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
=======
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
        enqueue_domain_event(ev_id)
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
        enqueue_domain_event(ev_id)
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
            enqueue_domain_event(ev_id)
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
        enqueue_domain_event(ev_id)

    logger.info("webhook_done topic=%s resource_id=%s", topic, resource_id)
>>>>>>> main
    return {"ok": True}
