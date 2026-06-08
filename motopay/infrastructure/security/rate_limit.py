from __future__ import annotations

import logging

import redis
from fastapi import HTTPException

from motopay.config import get_settings
from motopay.infrastructure.redis_client import get_redis_connection

logger = logging.getLogger(__name__)


def _assert_not_blocked(*, key: str, max_attempts: int, detail: str) -> None:
    settings = get_settings()
    if not settings.login_rate_limit_enabled:
        return
    try:
        raw = get_redis_connection().get(key)
    except redis.RedisError as e:
        logger.warning("rate_limit_check_failed key=%s: %s", key, e)
        return
    if raw is not None and int(raw) >= max_attempts:
        raise HTTPException(status_code=429, detail=detail)


def _record_failure(*, key: str, window_seconds: int) -> None:
    settings = get_settings()
    if not settings.login_rate_limit_enabled:
        return
    try:
        r = get_redis_connection()
        count = r.incr(key)
        if count == 1:
            r.expire(key, window_seconds)
    except redis.RedisError as e:
        logger.warning("rate_limit_record_failed key=%s: %s", key, e)


def _clear(*, key: str) -> None:
    if not get_settings().login_rate_limit_enabled:
        return
    try:
        get_redis_connection().delete(key)
    except redis.RedisError as e:
        logger.warning("rate_limit_clear_failed key=%s: %s", key, e)


def _login_key(ip: str, email: str) -> str:
    return f"login_rate:{ip}:{email.strip().lower()}"


def _refresh_key(ip: str) -> str:
    return f"refresh_rate:{ip}"


def _webhook_key(ip: str) -> str:
    return f"webhook_rate:{ip}"


def assert_login_not_blocked(ip: str, email: str) -> None:
    settings = get_settings()
    _assert_not_blocked(
        key=_login_key(ip, email),
        max_attempts=settings.login_rate_limit_max_attempts,
        detail="Muitas tentativas de login. Tente novamente mais tarde.",
    )


def record_login_failure(ip: str, email: str) -> None:
    settings = get_settings()
    _record_failure(
        key=_login_key(ip, email), window_seconds=settings.login_rate_limit_window_seconds
    )


def clear_login_attempts(ip: str, email: str) -> None:
    _clear(key=_login_key(ip, email))


def assert_refresh_not_blocked(ip: str) -> None:
    settings = get_settings()
    _assert_not_blocked(
        key=_refresh_key(ip),
        max_attempts=settings.refresh_rate_limit_max_attempts,
        detail="Muitas tentativas de renovação de sessão. Tente novamente mais tarde.",
    )


def record_refresh_failure(ip: str) -> None:
    settings = get_settings()
    _record_failure(key=_refresh_key(ip), window_seconds=settings.refresh_rate_limit_window_seconds)


def clear_refresh_attempts(ip: str) -> None:
    _clear(key=_refresh_key(ip))


def assert_webhook_not_blocked(ip: str) -> None:
    settings = get_settings()
    _assert_not_blocked(
        key=_webhook_key(ip),
        max_attempts=settings.webhook_rate_limit_max_attempts,
        detail="Muitas tentativas inválidas de webhook. Tente novamente mais tarde.",
    )


def record_webhook_failure(ip: str) -> None:
    settings = get_settings()
    _record_failure(key=_webhook_key(ip), window_seconds=settings.webhook_rate_limit_window_seconds)


def clear_webhook_attempts(ip: str) -> None:
    _clear(key=_webhook_key(ip))


def _portal_key(ip: str) -> str:
    return f"portal_rate:{ip}"


def assert_portal_not_blocked(ip: str) -> None:
    _assert_not_blocked(
        key=_portal_key(ip),
        max_attempts=60,  # 60 requisições por janela — tolerante o suficiente para uso legítimo
        detail="Muitas requisições ao portal de pagamento. Tente novamente em alguns minutos.",
    )


def record_portal_failure(ip: str) -> None:
    _record_failure(key=_portal_key(ip), window_seconds=300)  # janela de 5 min
