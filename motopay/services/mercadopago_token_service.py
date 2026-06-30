from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from motopay.domain.exceptions import MercadoPagoNotConnectedError
from motopay.infrastructure.crypto.token_encryption import encrypt_token
from motopay.infrastructure.db.models import Operacao
from motopay.infrastructure.payments.mercadopago_client import (
    MP_NOT_CONNECTED_MSG,
    MercadoPagoApiError,
    _allow_global_mp_token,
    is_valid_mp_access_token,
    mp_token_for_operacao,
    operacao_access_token_plain,
    operacao_refresh_token_plain,
    refresh_oauth_token,
)

logger = logging.getLogger(__name__)

_REFRESH_MARGIN = timedelta(minutes=5)


def _persist_mp_tokens(
    op: Operacao,
    *,
    access: str | None = None,
    refresh: str | None = None,
    public_key: str | None = None,
    expires_at: datetime | None = None,
    connection_status: str | None = None,
) -> None:
    if access is not None:
        op.mercadopago_access_token = encrypt_token(access) if access else None
    if refresh is not None:
        op.mercadopago_refresh_token = encrypt_token(refresh) if refresh else None
    if public_key is not None:
        op.mercadopago_public_key = public_key or None
    if expires_at is not None:
        op.mercadopago_oauth_expires_at = expires_at
    if connection_status is not None:
        op.mercadopago_connection_status = connection_status


def mark_mp_disconnected(db: Session, op: Operacao) -> None:
    op.mercadopago_access_token = None
    op.mercadopago_refresh_token = None
    op.mercadopago_public_key = None
    op.mercadopago_oauth_user_id = None
    op.mercadopago_oauth_expires_at = None
    op.mercadopago_account_email = None
    op.mercadopago_connection_status = "disconnected"
    db.add(op)
    db.commit()


def ensure_valid_mp_token(
    db: Session, op: Operacao | None, *, margin: timedelta = _REFRESH_MARGIN
) -> str:
    if op is None:
        if _allow_global_mp_token():
            return mp_token_for_operacao(op)
        raise MercadoPagoNotConnectedError(MP_NOT_CONNECTED_MSG)

    refresh = operacao_refresh_token_plain(op)
    expires_at = op.mercadopago_oauth_expires_at
    access = operacao_access_token_plain(op)

    if not refresh or expires_at is None:
        token = mp_token_for_operacao(op)
        if is_valid_mp_access_token(token):
            return token
        raise MercadoPagoNotConnectedError(MP_NOT_CONNECTED_MSG)

    now = datetime.now(UTC)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at > now + margin:
        if is_valid_mp_access_token(access):
            return access
        token = mp_token_for_operacao(op)
        if is_valid_mp_access_token(token):
            return token
        raise MercadoPagoNotConnectedError(MP_NOT_CONNECTED_MSG)

    # Token expira em breve: trava a linha da operação para serializar refresh concorrente
    # (dois webhooks/requests simultâneos não devem ambos chamar refresh_oauth_token com o
    # mesmo refresh_token de uso único). Double-checked locking: outro request pode já ter
    # renovado enquanto esperávamos o lock.
    locked = db.scalars(
        select(Operacao).where(Operacao.id == op.id).with_for_update()
    ).first()
    if locked is not None:
        op = locked
        access = operacao_access_token_plain(op)
        refresh = operacao_refresh_token_plain(op) or refresh
        exp2 = op.mercadopago_oauth_expires_at
        if exp2 is not None:
            if exp2.tzinfo is None:
                exp2 = exp2.replace(tzinfo=UTC)
            if exp2 > now + margin and is_valid_mp_access_token(access):
                return access

    try:
        data = refresh_oauth_token(refresh_token=refresh)
    except MercadoPagoApiError:
        logger.warning("mp_refresh_failed operacao_id=%s", op.id)
        mark_mp_disconnected(db, op)
        raise MercadoPagoNotConnectedError(MP_NOT_CONNECTED_MSG) from None

    new_access = str(data.get("access_token", "")).strip()
    if not new_access:
        logger.warning("mp_refresh_empty_access operacao_id=%s", op.id)
        mark_mp_disconnected(db, op)
        raise MercadoPagoNotConnectedError(MP_NOT_CONNECTED_MSG)

    new_refresh = data.get("refresh_token")
    public_key = data.get("public_key")
    expires_in = data.get("expires_in")
    new_expires = (
        now + timedelta(seconds=int(expires_in)) if expires_in is not None else None
    )
    _persist_mp_tokens(
        op,
        access=new_access,
        refresh=str(new_refresh) if new_refresh else refresh,
        public_key=str(public_key) if public_key else None,
        expires_at=new_expires,
        connection_status="connected",
    )
    db.add(op)
    db.commit()
    db.refresh(op)
    return new_access


def refresh_expiring_mp_oauth_tokens(
    db: Session, *, window: timedelta = timedelta(days=7)
) -> int:
    """Renova proativamente tokens OAuth que expiram dentro da janela."""
    cutoff = datetime.now(UTC) + window
    ops = db.scalars(
        select(Operacao).where(
            Operacao.mercadopago_refresh_token.isnot(None),
            Operacao.mercadopago_refresh_token != "",
            Operacao.mercadopago_oauth_expires_at.isnot(None),
            Operacao.mercadopago_oauth_expires_at < cutoff,
            Operacao.mercadopago_connection_status == "connected",
        )
    ).all()
    refreshed = 0
    for op in ops:
        try:
            ensure_valid_mp_token(db, op, margin=window)
            refreshed += 1
        except MercadoPagoNotConnectedError:
            logger.warning("proactive_mp_oauth_refresh_disconnected operacao=%s", op.id)
        except Exception:
            logger.exception("proactive_mp_oauth_refresh_failed operacao=%s", op.id)
    if ops:
        logger.info(
            "proactive_mp_oauth_refresh total=%s refreshed=%s", len(ops), refreshed
        )
    return refreshed


def disconnect_mercadopago_oauth(db: Session, op: Operacao) -> None:
    mark_mp_disconnected(db, op)
