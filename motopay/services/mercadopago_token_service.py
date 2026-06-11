from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from motopay.infrastructure.db.models import Operacao
from motopay.infrastructure.payments.mercadopago_client import (
    MercadoPagoApiError,
    mp_token_for_operacao,
    refresh_oauth_token,
)

logger = logging.getLogger(__name__)

_REFRESH_MARGIN = timedelta(minutes=5)


def ensure_valid_mp_token(
    db: Session, op: Operacao | None, *, margin: timedelta = _REFRESH_MARGIN
) -> str:
    if op is None:
        return mp_token_for_operacao(op)
    refresh = (op.mercadopago_refresh_token or "").strip()
    expires_at = op.mercadopago_oauth_expires_at
    if not refresh or expires_at is None:
        return mp_token_for_operacao(op)
    now = datetime.now(UTC)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at > now + margin:
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


def refresh_expiring_mp_oauth_tokens(
    db: Session, *, window: timedelta = timedelta(days=7)
) -> int:
    """Renova proativamente tokens OAuth que expiram dentro da janela.

    O refresh token do MP é single-use: a renovação precisa passar pelo mesmo
    caminho que persiste o token rotacionado (ensure_valid_mp_token).
    """
    cutoff = datetime.now(UTC) + window
    ops = db.scalars(
        select(Operacao).where(
            Operacao.mercadopago_refresh_token.isnot(None),
            Operacao.mercadopago_refresh_token != "",
            Operacao.mercadopago_oauth_expires_at.isnot(None),
            Operacao.mercadopago_oauth_expires_at < cutoff,
        )
    ).all()
    refreshed = 0
    for op in ops:
        try:
            ensure_valid_mp_token(db, op, margin=window)
            refreshed += 1
        except Exception:  # uma operação com problema não pode abortar o lote
            logger.exception("proactive_mp_oauth_refresh_failed operacao=%s", op.id)
    if ops:
        logger.info(
            "proactive_mp_oauth_refresh total=%s refreshed=%s", len(ops), refreshed
        )
    return refreshed


def disconnect_mercadopago_oauth(db: Session, op: Operacao) -> None:
    op.mercadopago_access_token = None
    op.mercadopago_refresh_token = None
    op.mercadopago_oauth_user_id = None
    op.mercadopago_oauth_expires_at = None
    db.add(op)
    db.commit()
