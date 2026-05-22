from __future__ import annotations

import logging
import secrets

import redis

from motopay.config import get_settings
from motopay.infrastructure.redis_client import get_redis_connection

logger = logging.getLogger(__name__)

_PREFIX = "refresh:"


def _ttl_seconds() -> int:
    return get_settings().refresh_token_expire_days * 24 * 3600


def create_refresh_token(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    try:
        get_redis_connection().setex(f"{_PREFIX}{token}", _ttl_seconds(), str(user_id))
    except redis.RedisError as e:
        logger.error("refresh_token_create_failed user_id=%s: %s", user_id, e)
        raise
    return token


def validate_refresh_token(token: str) -> int | None:
    if not token.strip():
        return None
    try:
        raw = get_redis_connection().get(f"{_PREFIX}{token}")
    except redis.RedisError as e:
        logger.warning("refresh_token_validate_failed: %s", e)
        return None
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def revoke_refresh_token(token: str) -> None:
    if not token.strip():
        return
    try:
        get_redis_connection().delete(f"{_PREFIX}{token}")
    except redis.RedisError as e:
        logger.warning("refresh_token_revoke_failed: %s", e)


def revoke_all_refresh_tokens_for_user(user_id: int) -> int:
    """Remove todos refresh tokens do usuário (scan por padrão)."""
    r = get_redis_connection()
    removed = 0
    try:
        for key in r.scan_iter(f"{_PREFIX}*"):
            raw = r.get(key)
            if raw is not None and int(raw) == user_id:
                r.delete(key)
                removed += 1
    except (redis.RedisError, ValueError) as e:
        logger.warning("refresh_token_revoke_all_failed user_id=%s: %s", user_id, e)
    return removed
