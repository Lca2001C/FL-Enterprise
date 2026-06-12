from __future__ import annotations

import logging

import pytest
from motopay.config.settings import Settings, get_settings


@pytest.fixture(autouse=True)
def _reset_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _base_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pw@prod-db.example:5432/motopay")
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET", "x" + "a" * 48)
    monkeypatch.setenv("MERCADOPAGO_ACCESS_TOKEN", "mp-token")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("REDIS_URL", "rediss://:strong-redis-secret@redis.example:6380/0")
    monkeypatch.setenv(
        "CORS_ORIGINS", "https://admin.example.test"
    )
    monkeypatch.delenv("ALLOW_PRODUCTION_WITHOUT_MERCADOPAGO", raising=False)
    monkeypatch.delenv("ALLOW_PRODUCTION_WITHOUT_TELEGRAM", raising=False)


def test_production_loads_when_strict_requirements_met(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_production(monkeypatch)
    s = get_settings()
    assert s.environment == "production"


def test_production_requires_mercadopago_token(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_production(monkeypatch)
    monkeypatch.setenv("MERCADOPAGO_ACCESS_TOKEN", "")
    with pytest.raises(RuntimeError, match="MERCADOPAGO_ACCESS_TOKEN"):
        Settings()


def test_production_optional_mercadopago_with_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_production(monkeypatch)
    monkeypatch.setenv("MERCADOPAGO_ACCESS_TOKEN", "")
    monkeypatch.setenv("ALLOW_PRODUCTION_WITHOUT_MERCADOPAGO", "true")
    Settings()


def test_production_requires_telegram(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_production(monkeypatch)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "")
    with pytest.raises(RuntimeError, match="TELEGRAM_BOT_TOKEN"):
        Settings()


def test_production_warnings_localhost_redis_and_empty_cors(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    _base_production(monkeypatch)
    monkeypatch.setenv("REDIS_URL", "redis://:strongpass@localhost:6379/0")
    monkeypatch.setenv("CORS_ORIGINS", "")
    caplog.set_level(logging.WARNING)
    Settings()
    messages = [r.getMessage() for r in caplog.records]
    assert any("REDIS_URL" in m and "localhost" in m.lower() for m in messages)
    assert any("CORS_ORIGINS" in m for m in messages)


def test_production_rejects_default_postgres_password(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_production(monkeypatch)
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+psycopg://postgres:postgres@prod-db.example:5432/motopay"
    )
    with pytest.raises(RuntimeError, match="POSTGRES_PASSWORD"):
        Settings()


def test_production_rejects_redis_without_password(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_production(monkeypatch)
    monkeypatch.setenv("REDIS_URL", "redis://redis.example:6379/0")
    monkeypatch.delenv("ALLOW_PRODUCTION_REDIS_WITHOUT_AUTH", raising=False)
    with pytest.raises(RuntimeError, match="REDIS_URL"):
        Settings()


def test_production_allows_redis_without_password_with_flag(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    # Redis gerenciado de rede privada sem senha (ex.: Render Key Value interno).
    _base_production(monkeypatch)
    monkeypatch.setenv("REDIS_URL", "redis://red-abc123:6379")
    monkeypatch.setenv("ALLOW_PRODUCTION_REDIS_WITHOUT_AUTH", "true")
    caplog.set_level(logging.WARNING)
    s = Settings()
    assert s.allow_production_redis_without_auth is True
    assert any("ALLOW_PRODUCTION_REDIS_WITHOUT_AUTH" in r.getMessage() for r in caplog.records)


def test_production_disables_webhook_query_token(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_production(monkeypatch)
    s = Settings()
    assert s.allow_webhook_token_in_query is False


def test_database_url_render_style_gets_psycopg_driver(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://motopay:secret@dpg-xxxx-a/motopay",
    )
    s = Settings()
    assert s.database_url.startswith("postgresql+psycopg://")
    assert "dpg-xxxx-a" in s.database_url


def test_database_url_postgres_scheme_gets_psycopg_driver(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgres://user:pw@host:5432/db")
    s = Settings()
    assert s.database_url == "postgresql+psycopg://user:pw@host:5432/db"


def test_redis_url_without_scheme_gets_prefixed(monkeypatch: pytest.MonkeyPatch) -> None:
    # Host copiado do Render Key Value sem 'redis://' — deve ser normalizado.
    monkeypatch.setenv("REDIS_URL", "red-abc123:6379")
    s = Settings()
    assert s.redis_url == "redis://red-abc123:6379"


def test_redis_url_empty_means_degraded_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REDIS_URL", "")
    s = Settings()
    assert s.redis_url == ""


def test_redis_url_with_scheme_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REDIS_URL", "rediss://:secret@host.example:6380/0")
    s = Settings()
    assert s.redis_url == "rediss://:secret@host.example:6380/0"


def test_production_reports_all_missing_vars_at_once(monkeypatch: pytest.MonkeyPatch) -> None:
    # Vários problemas simultâneos: a mensagem deve listar TODOS (sem "gato e rato").
    _base_production(monkeypatch)
    monkeypatch.setenv("MERCADOPAGO_ACCESS_TOKEN", "")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "")
    monkeypatch.setenv("REDIS_URL", "redis://redis.example:6379/0")
    monkeypatch.delenv("ALLOW_PRODUCTION_REDIS_WITHOUT_AUTH", raising=False)
    with pytest.raises(RuntimeError) as exc:
        Settings()
    msg = str(exc.value)
    assert "MERCADOPAGO_ACCESS_TOKEN" in msg
    assert "TELEGRAM_BOT_TOKEN" in msg
    assert "REDIS_URL" in msg
