"""Modo sem Redis (REDIS_URL vazio): shim em memória + boot degradado."""

from __future__ import annotations

import logging

import pytest
from motopay.config.settings import Settings, get_settings
from motopay.infrastructure.redis_client import (
    InMemoryRedis,
    get_redis_connection,
    redis_enabled,
    redis_using_memory,
)
from motopay.infrastructure.security.refresh_tokens import create_refresh_token


@pytest.fixture
def no_redis(monkeypatch: pytest.MonkeyPatch):
    """Força modo sem-Redis de forma determinística (ignora o .env local)."""
    from motopay.infrastructure import redis_client

    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.setenv("REDIS_URL", "")
    get_settings.cache_clear()
    redis_client.reset_redis_connection()
    yield
    redis_client.reset_redis_connection()
    get_settings.cache_clear()


def test_get_connection_returns_inmemory_when_unset(no_redis):
    assert isinstance(get_redis_connection(), InMemoryRedis)


def test_get_connection_falls_back_when_redis_unreachable(monkeypatch: pytest.MonkeyPatch):
    """REDIS_URL inválido não deve derrubar login (usa InMemoryRedis após ping falhar)."""
    from motopay.infrastructure import redis_client

    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:59999/0")
    get_settings.cache_clear()
    redis_client.reset_redis_connection()
    conn = get_redis_connection()
    assert isinstance(conn, InMemoryRedis)
    assert redis_using_memory() is True
    assert redis_enabled() is False
    assert conn.setex("refresh:test", 60, "1") is True
    redis_client.reset_redis_connection()
    get_settings.cache_clear()


def test_create_refresh_token_with_unreachable_redis(monkeypatch: pytest.MonkeyPatch):
    """Login não pode falhar com 500 só porque REDIS_URL aponta para host inacessível."""
    from motopay.infrastructure import redis_client

    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:59999/0")
    get_settings.cache_clear()
    redis_client.reset_redis_connection()
    token = create_refresh_token(99)
    assert len(token) >= 32
    redis_client.reset_redis_connection()
    get_settings.cache_clear()


def test_inmemory_string_ops():
    r = InMemoryRedis()
    assert r.get("k") is None
    assert r.set("k", "v") is True
    assert r.get("k") == "v"
    assert r.delete("k") == 1
    assert r.get("k") is None


def test_inmemory_set_nx():
    r = InMemoryRedis()
    assert r.set("once", "1", nx=True, ex=900) is True
    assert r.set("once", "2", nx=True, ex=900) is None  # já existe → não sobrescreve
    assert r.get("once") == "1"


def test_inmemory_incr_and_expire():
    r = InMemoryRedis()
    assert r.incr("c") == 1
    assert r.incr("c") == 2
    assert r.expire("c", 60) is True
    assert r.expire("missing", 60) is False


def test_inmemory_setex_and_scan_iter():
    r = InMemoryRedis()
    r.setex("refresh:abc", 3600, "7")
    r.setex("refresh:def", 3600, "9")
    r.setex("other:x", 3600, "1")
    keys = set(r.scan_iter("refresh:*"))
    assert keys == {"refresh:abc", "refresh:def"}


def test_inmemory_publish_and_ping_noop():
    r = InMemoryRedis()
    assert r.publish("ch", "msg") == 0
    assert r.ping() is True
    # método não implementado → no-op seguro
    assert r.zadd("k", {"a": 1}) is None


def test_rate_limiter_does_not_crash_without_redis(no_redis):
    from motopay.security.rate_limiter import RateLimiter

    rl = RateLimiter()
    result = rl.check("ip:1.2.3.4", limit=5, window_seconds=60)
    assert result.allowed is True


@pytest.mark.asyncio
async def test_health_redis_degraded_when_unconfigured(no_redis):
    from motopay.health.checks import HealthStatus, check_redis

    result = await check_redis()
    assert result.name == "redis"
    assert result.status == HealthStatus.DEGRADED
    assert "degradado" in (result.error or "").lower()


def test_inmemory_pubsub_noop():
    r = InMemoryRedis()
    ps = r.pubsub()
    ps.psubscribe("events:*")
    assert ps.get_message(timeout=1.0) is None


def test_production_boots_without_redis(monkeypatch: pytest.MonkeyPatch, caplog):
    # Produção com REDIS_URL vazio: sobe (modo degradado), sem erro.
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pw@prod-db.example:5432/motopay")
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET", "x" + "a" * 48)
    monkeypatch.setenv("MERCADOPAGO_ACCESS_TOKEN", "mp-token")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("CORS_ORIGINS", "https://admin.example.test")
    # Sem REDIS_URL no ambiente + _env_file=None → cai no default vazio (modo sem-Redis).
    monkeypatch.delenv("REDIS_URL", raising=False)
    get_settings.cache_clear()
    caplog.set_level(logging.WARNING)
    s = Settings(_env_file=None)
    assert s.redis_url == ""
    assert any("MODO DEGRADADO" in r.getMessage() for r in caplog.records)
    get_settings.cache_clear()
