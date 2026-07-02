from __future__ import annotations

import logging
import secrets

import redis

from motopay.config import get_settings
from motopay.infrastructure.redis_client import get_redis_connection, reset_redis_connection

logger = logging.getLogger(__name__)

_PREFIX = "refresh:"
_EPOCH_PREFIX = "refresh_epoch:"


def _ttl_seconds() -> int:
    return get_settings().refresh_token_expire_days * 24 * 3600


def _current_epoch(r, user_id: int) -> int:
    """Época de revogação do usuário. Incrementá-la invalida, de forma atômica,
    todos os tokens emitidos antes — sem a janela de corrida do SCAN+DELETE."""
    raw = r.get(f"{_EPOCH_PREFIX}{user_id}")
    try:
        return int(raw) if raw is not None else 0
    except (TypeError, ValueError):
        return 0


def create_refresh_token(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    key = f"{_PREFIX}{token}"
    ttl = _ttl_seconds()
    for attempt in range(2):
        try:
            r = get_redis_connection()
            # Carimba o token com a época atual do usuário (user_id:epoch).
            r.setex(key, ttl, f"{user_id}:{_current_epoch(r, user_id)}")
            return token
        except redis.RedisError as e:
            if attempt == 0:
                logger.warning(
                    "refresh_token_create_failed user_id=%s (tentativa %s): %s — reconectando",
                    user_id,
                    attempt + 1,
                    e,
                )
                reset_redis_connection()
                continue
            logger.error("refresh_token_create_failed user_id=%s: %s", user_id, e)
            raise
    return token


def validate_refresh_token(token: str) -> int | None:
    if not token.strip():
        return None
    try:
        r = get_redis_connection()
        raw = r.get(f"{_PREFIX}{token}")
    except redis.RedisError as e:
        logger.warning("refresh_token_validate_failed: %s", e)
        return None
    if raw is None:
        return None
    # Valor pode ser "user_id" (legado) ou "user_id:epoch".
    parts = str(raw).split(":", 1)
    try:
        user_id = int(parts[0])
    except (TypeError, ValueError):
        return None
    token_epoch = 0
    if len(parts) == 2:
        try:
            token_epoch = int(parts[1])
        except (TypeError, ValueError):
            token_epoch = 0
    # Token emitido antes de uma revogação-em-massa (época menor) é rejeitado.
    if token_epoch < _current_epoch(r, user_id):
        return None
    return user_id


def revoke_refresh_token(token: str) -> None:
    if not token.strip():
        return
    try:
        get_redis_connection().delete(f"{_PREFIX}{token}")
    except redis.RedisError as e:
        logger.warning("refresh_token_revoke_failed: %s", e)


def revoke_all_refresh_tokens_for_user(user_id: int) -> int:
    """Revoga todos os refresh tokens do usuário.

    Incrementa a época de revogação (operação atômica INCR) — qualquer token com época
    anterior passa a ser rejeitado em validate_refresh_token, eliminando a janela de corrida
    do SCAN+DELETE (um token emitido durante o scan não escapa mais). Também remove as chaves
    existentes em best-effort para liberar memória.
    """
    r = get_redis_connection()
    removed = 0
    try:
        # Invalidação atômica: nada emitido antes deste ponto continua válido.
        r.incr(f"{_EPOCH_PREFIX}{user_id}")
        r.expire(f"{_EPOCH_PREFIX}{user_id}", _ttl_seconds())
    except redis.RedisError as e:
        logger.warning("refresh_token_epoch_bump_failed user_id=%s: %s", user_id, e)
    try:
        for key in r.scan_iter(f"{_PREFIX}*"):
            raw = r.get(key)
            if raw is not None and str(raw).split(":", 1)[0] == str(user_id):
                r.delete(key)
                removed += 1
    except (redis.RedisError, ValueError) as e:
        logger.warning("refresh_token_revoke_all_failed user_id=%s: %s", user_id, e)
    return removed
