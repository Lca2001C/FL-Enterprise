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
    monkeypatch.setenv("ASAAS_WEBHOOK_TOKEN", "wh-secret")
    monkeypatch.setenv("ASAAS_API_KEY", "k")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("ASAAS_API_BASE_URL", "https://api.asaas.com/api/v3")
    monkeypatch.setenv("REDIS_URL", "rediss://redis.example:6380/0")
    monkeypatch.setenv(
        "CORS_ORIGINS", "https://admin.example.test"
    )  # evita `.env` local vazio sobrescrever intenções do caso
    monkeypatch.delenv("ALLOW_PRODUCTION_WITHOUT_ASAAS", raising=False)
    monkeypatch.delenv("ALLOW_PRODUCTION_WITHOUT_TELEGRAM", raising=False)
    monkeypatch.delenv("ALLOW_ASAAS_SANDBOX_IN_PRODUCTION", raising=False)


def test_production_loads_when_strict_requirements_met(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_production(monkeypatch)
    s = get_settings()
    assert s.environment == "production"


def test_production_rejects_sandbox_without_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_production(monkeypatch)
    monkeypatch.setenv("ASAAS_API_BASE_URL", "https://sandbox.asaas.com/api/v3")
    with pytest.raises(RuntimeError, match="sandbox"):
        Settings()


def test_production_allows_sandbox_with_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_production(monkeypatch)
    monkeypatch.setenv("ASAAS_API_BASE_URL", "https://sandbox.asaas.com/api/v3")
    monkeypatch.setenv("ALLOW_ASAAS_SANDBOX_IN_PRODUCTION", "true")
    Settings()


def test_production_requires_asaas_key(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_production(monkeypatch)
    monkeypatch.setenv("ASAAS_API_KEY", "")
    with pytest.raises(RuntimeError, match="ASAAS_API_KEY"):
        Settings()


def test_production_optional_asaas_with_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_production(monkeypatch)
    monkeypatch.setenv("ASAAS_API_KEY", "")
    monkeypatch.setenv("ALLOW_PRODUCTION_WITHOUT_ASAAS", "true")
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
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("CORS_ORIGINS", "")
    caplog.set_level(logging.WARNING)
    Settings()
    messages = [r.getMessage() for r in caplog.records]
    assert any("REDIS_URL" in m and "localhost" in m.lower() for m in messages)
    assert any("CORS_ORIGINS" in m for m in messages)
