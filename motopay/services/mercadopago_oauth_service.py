from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import redis
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from motopay.config import get_settings
from motopay.domain.enums import UserRole
from motopay.domain.exceptions import ForbiddenError, NotFoundError
from motopay.infrastructure.db.models import Operacao
from motopay.infrastructure.payments.mercadopago_client import (
    MercadoPagoApiError,
    build_oauth_authorization_url,
    exchange_oauth_code,
    mercadopago_api_error_message,
)
from motopay.infrastructure.redis_client import get_redis_connection
from motopay.interfaces.api.deps import CurrentUser
from motopay.services.billing_service import _effective_operacao
from motopay.services.mercadopago_token_service import disconnect_mercadopago_oauth

logger = logging.getLogger(__name__)

# Casa com o exp do JWT de state: após expirar o JWT a chave Redis não é mais necessária.
_STATE_TTL_SECONDS = 15 * 60


def _oauth_redirect_uri() -> str:
    s = get_settings()
    explicit = s.mercadopago_oauth_redirect_uri.strip()
    if explicit:
        return explicit
    return f"{s.api_public_base_url.rstrip('/')}/api/v1/operacoes/mp-oauth/callback"


def _encode_oauth_state(*, operacao_id: int, user_id: int) -> str:
    s = get_settings()
    payload = {
        "operacao_id": operacao_id,
        "user_id": user_id,
        "jti": uuid4().hex,
        "exp": datetime.now(UTC) + timedelta(seconds=_STATE_TTL_SECONDS),
    }
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm)


def _decode_oauth_state(state: str) -> tuple[int, int, str]:
    s = get_settings()
    try:
        data = jwt.decode(state, s.jwt_secret, algorithms=[s.jwt_algorithm])
        jti = str(data["jti"])
        if not jti:
            raise ValueError("jti vazio")
        return int(data["operacao_id"]), int(data["user_id"]), jti
    except (JWTError, KeyError, TypeError, ValueError) as exc:
        raise ForbiddenError("State OAuth inválido ou expirado") from exc


def _assert_state_not_used(jti: str) -> None:
    """Garante uso único do state (anti-replay do callback, que é público)."""
    try:
        r = get_redis_connection()
        if not r.set(f"mp_oauth_state_used:{jti}", "1", nx=True, ex=_STATE_TTL_SECONDS):
            raise ForbiddenError("State OAuth já utilizado")
    except redis.RedisError as e:
        # Fail-open deliberado (mesma filosofia de rate_limit.py): Redis fora do ar
        # não pode bloquear a conexão OAuth, mas a janela sem proteção gera alerta.
        logger.error("mp_oauth_state_replay_check_failed (fail-open) jti=%s: %s", jti, e)


def start_mercadopago_oauth(
    db: Session,
    user: CurrentUser,
    operacao_scope: int | None,
) -> dict[str, str]:
    del db
    operacao_id = _effective_operacao(user, operacao_scope)
    if user.role == UserRole.DONO and user.operacao_id != operacao_id:
        raise ForbiddenError("Operação fora do escopo")
    redirect_uri = _oauth_redirect_uri()
    state = _encode_oauth_state(operacao_id=operacao_id, user_id=user.id)
    try:
        url = build_oauth_authorization_url(state=state, redirect_uri=redirect_uri)
    except ValueError as exc:
        raise ForbiddenError(str(exc)) from exc
    return {"authorization_url": url, "redirect_uri": redirect_uri}


def complete_mercadopago_oauth(
    db: Session,
    *,
    code: str,
    state: str,
) -> Operacao:
    operacao_id, _user_id, jti = _decode_oauth_state(state)
    # Marca o state como usado ANTES da troca de código: um replay nunca chega ao MP.
    # Se a troca falhar, o usuário simplesmente clica em "Conectar" de novo (novo state).
    _assert_state_not_used(jti)
    op = db.get(Operacao, operacao_id)
    if not op:
        raise NotFoundError("Operação não encontrada")
    redirect_uri = _oauth_redirect_uri()
    try:
        data = exchange_oauth_code(code=code, redirect_uri=redirect_uri)
    except MercadoPagoApiError as exc:
        raise ForbiddenError(
            f"Falha ao conectar Mercado Pago: {mercadopago_api_error_message(exc)}"
        ) from exc
    op.mercadopago_access_token = str(data.get("access_token", ""))
    op.mercadopago_public_key = str(data.get("public_key", "")) or op.mercadopago_public_key
    refresh = data.get("refresh_token")
    if refresh:
        op.mercadopago_refresh_token = str(refresh)
    user_id = data.get("user_id")
    if user_id is not None:
        op.mercadopago_oauth_user_id = str(user_id)
    expires_in = data.get("expires_in")
    if expires_in is not None:
        op.mercadopago_oauth_expires_at = datetime.now(UTC) + timedelta(seconds=int(expires_in))
    db.add(op)
    db.commit()
    db.refresh(op)
    return op


def disconnect_mercadopago_oauth_for_operacao(
    db: Session,
    user: CurrentUser,
    operacao_scope: int | None,
) -> None:
    operacao_id = _effective_operacao(user, operacao_scope)
    if user.role == UserRole.DONO and user.operacao_id != operacao_id:
        raise ForbiddenError("Operação fora do escopo")
    op = db.get(Operacao, operacao_id)
    if not op:
        raise NotFoundError("Operação não encontrada")
    disconnect_mercadopago_oauth(db, op)
