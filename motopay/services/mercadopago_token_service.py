from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from motopay.infrastructure.db.models import Operacao
from motopay.infrastructure.payments.mercadopago_client import (
    MercadoPagoApiError,
    mp_token_for_operacao,
    refresh_oauth_token,
)

logger = logging.getLogger(__name__)

_REFRESH_MARGIN = timedelta(minutes=5)


def ensure_valid_mp_token(db: Session, op: Operacao | None) -> str:
    if op is None:
        return mp_token_for_operacao(op)
    refresh = (op.mercadopago_refresh_token or "").strip()
    expires_at = op.mercadopago_oauth_expires_at
    if not refresh or expires_at is None:
        return mp_token_for_operacao(op)
    now = datetime.now(UTC)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at > now + _REFRESH_MARGIN:
        return mp_token_for_operacao(op)
    try:
        data = refresh_oauth_token(refresh_token=refresh)
    except MercadoPagoApiError:
        logger.exception("Falha ao renovar token OAuth operacao=%s", op.id)
        return mp_token_for_operacao(op)
    access = str(data.get("access_token", "")).strip()
    if access:
        op.mercadopago_access_token = access
    new_refresh = data.get("refresh_token")
    if new_refresh:
        op.mercadopago_refresh_token = str(new_refresh)
    public_key = data.get("public_key")
    if public_key:
        op.mercadopago_public_key = str(public_key)
    expires_in = data.get("expires_in")
    if expires_in is not None:
        op.mercadopago_oauth_expires_at = now + timedelta(seconds=int(expires_in))
    db.add(op)
    db.commit()
    db.refresh(op)
    return mp_token_for_operacao(op)


def disconnect_mercadopago_oauth(db: Session, op: Operacao) -> None:
    op.mercadopago_access_token = None
    op.mercadopago_refresh_token = None
    op.mercadopago_oauth_user_id = None
    op.mercadopago_oauth_expires_at = None
    db.add(op)
    db.commit()
