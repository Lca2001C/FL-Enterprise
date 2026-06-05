from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from motopay.domain.enums import CobrancaStatus
from motopay.infrastructure.db.models import Cobranca, Operacao
from motopay.infrastructure.payments.mercadopago_client import (
    MercadoPagoApiError,
    MercadoPagoClient,
    mp_configured_for_operacao,
)
from motopay.infrastructure.payments.order_utils import is_order_paid, order_total_amount
from motopay.services.billing_service import (
    handle_mercadopago_chargeback,
    handle_mercadopago_order_confirmed,
    handle_mercadopago_payment_confirmed,
    sync_refund_from_mercadopago_payment,
)
from motopay.services.mercadopago_token_service import ensure_valid_mp_token

logger = logging.getLogger(__name__)

_MP_CONFIRMED = frozenset({"approved", "authorized"})
_OPEN_CHARGE_STATUSES = (CobrancaStatus.PENDENTE.value, CobrancaStatus.ATRASADO.value)
_CHARGEBACK_OPEN = frozenset({"opened", "under_review", "in_process", "pending"})


def reconcile_pending_mercadopago_payments(db: Session, *, limit: int = 100) -> int:
    """Confirma cobranças abertas cujo pagamento já foi aprovado no MP (backup ao webhook)."""
    rows = list(
        db.scalars(
            select(Cobranca)
            .where(
                Cobranca.status.in_(_OPEN_CHARGE_STATUSES),
                Cobranca.mercadopago_order_id.isnot(None),
            )
            .order_by(Cobranca.id.desc())
            .limit(limit)
        ).all()
    )
    confirmed = 0
    for cob in rows:
        op = db.get(Operacao, cob.operacao_id)
        if not op or not mp_configured_for_operacao(op):
            continue
        token = ensure_valid_mp_token(db, op)
        client = MercadoPagoClient(access_token=token)
        try:
            order_data = client.get_order(cob.mercadopago_order_id)
        except MercadoPagoApiError:
            continue
        if not is_order_paid(order_data):
            if cob.mercadopago_payment_id:
                try:
                    pay = client.get_payment(cob.mercadopago_payment_id)
                except MercadoPagoApiError:
                    continue
                if str(pay.get("status", "")).lower() not in _MP_CONFIRMED:
                    continue
                amount = pay.get("transaction_amount")
                val = Decimal(str(amount)) if amount is not None else None
                ok, _ = handle_mercadopago_payment_confirmed(
                    db, mercadopago_payment_id=cob.mercadopago_payment_id, value=val
                )
                if ok:
                    confirmed += 1
            continue
        amount = order_total_amount(order_data)
        ok, _ = handle_mercadopago_order_confirmed(
            db,
            mercadopago_order_id=cob.mercadopago_order_id,
            order_data=order_data,
            value=amount,
        )
        if ok:
            confirmed += 1
    if confirmed:
        logger.info("Reconciliação MP: %s cobrança(s) confirmada(s)", confirmed)
    return confirmed


def reconcile_mercadopago_refunds(db: Session, *, limit: int = 50) -> int:
    rows = list(
        db.scalars(
            select(Cobranca)
            .where(
                Cobranca.status.in_((CobrancaStatus.RECEBIDO.value, CobrancaStatus.CANCELADO.value)),
                Cobranca.mercadopago_payment_id.isnot(None),
            )
            .order_by(Cobranca.id.desc())
            .limit(limit)
        ).all()
    )
    synced = 0
    for cob in rows:
        op = db.get(Operacao, cob.operacao_id)
        if not op or not mp_configured_for_operacao(op):
            continue
        client = MercadoPagoClient(access_token=ensure_valid_mp_token(db, op))
        try:
            pay = client.get_payment(cob.mercadopago_payment_id)
        except MercadoPagoApiError:
            continue
        ok, _ = sync_refund_from_mercadopago_payment(db, pay_data=pay)
        if ok:
            synced += 1
    return synced


def reconcile_mercadopago_chargebacks(db: Session, *, limit: int = 50) -> int:
    rows = list(
        db.scalars(
            select(Cobranca)
            .where(
                Cobranca.mercadopago_dispute_status.isnot(None),
                Cobranca.mercadopago_payment_id.isnot(None),
            )
            .order_by(Cobranca.id.desc())
            .limit(limit)
        ).all()
    )
    updated = 0
    for cob in rows:
        status = (cob.mercadopago_dispute_status or "").lower()
        if status and status not in _CHARGEBACK_OPEN:
            continue
        op = db.get(Operacao, cob.operacao_id)
        if not op or not mp_configured_for_operacao(op):
            continue
        client = MercadoPagoClient(access_token=ensure_valid_mp_token(db, op))
        try:
            pay = client.get_payment(cob.mercadopago_payment_id)
        except MercadoPagoApiError:
            continue
        cb_id = pay.get("chargeback_id") or pay.get("id")
        if not cb_id:
            continue
        try:
            cb_data = client.get_chargeback(str(cb_id))
        except MercadoPagoApiError:
            continue
        ok, _ = handle_mercadopago_chargeback(db, chargeback_data=cb_data)
        if ok:
            updated += 1
    return updated


def reconcile_expired_pix_orders(db: Session, *, limit: int = 50) -> int:
    rows = list(
        db.scalars(
            select(Cobranca)
            .where(
                Cobranca.status.in_(_OPEN_CHARGE_STATUSES),
                Cobranca.mercadopago_order_id.isnot(None),
                Cobranca.pix_copia_cola.isnot(None),
            )
            .order_by(Cobranca.id.desc())
            .limit(limit)
        ).all()
    )
    cleared = 0
    for cob in rows:
        op = db.get(Operacao, cob.operacao_id)
        if not op or not mp_configured_for_operacao(op):
            continue
        client = MercadoPagoClient(access_token=ensure_valid_mp_token(db, op))
        try:
            order_data = client.get_order(cob.mercadopago_order_id)
        except MercadoPagoApiError:
            continue
        if is_order_paid(order_data):
            continue
        status = str(order_data.get("status", "")).lower()
        if status not in ("expired", "cancelled", "canceled"):
            continue
        cob.pix_copia_cola = None
        cob.mercadopago_order_id = None
        cob.mercadopago_payment_id = None
        db.add(cob)
        cleared += 1
    if cleared:
        db.commit()
        logger.info("Reconciliação MP: %s Pix expirado(s) limpo(s)", cleared)
    return cleared


def reconcile_all_mercadopago(db: Session) -> int:
    total = 0
    total += reconcile_pending_mercadopago_payments(db)
    total += reconcile_mercadopago_refunds(db)
    total += reconcile_mercadopago_chargebacks(db)
    total += reconcile_expired_pix_orders(db)
    return total
