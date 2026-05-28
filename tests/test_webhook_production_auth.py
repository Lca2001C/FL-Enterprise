from __future__ import annotations

import pytest
from motopay.config import get_settings


@pytest.fixture
def production_webhook_env(monkeypatch: pytest.MonkeyPatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET", "x" + "a" * 48)
    monkeypatch.setenv("MERCADOPAGO_ACCESS_TOKEN", "mp-token")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pw@prod-db.example:5432/motopay")
    monkeypatch.setenv("REDIS_URL", "rediss://:strong-redis-secret@redis.example:6380/0")
    monkeypatch.setenv("CORS_ORIGINS", "https://admin.example.test")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_mercadopago_webhook_rejects_bad_signature_in_production(
    client, production_webhook_env, monkeypatch
):
    monkeypatch.setenv("MERCADOPAGO_WEBHOOK_SECRET", "prod-mp-secret")
    get_settings.cache_clear()
    response = client.post(
        "/webhooks/mercadopago",
        headers={"x-signature": "wrong"},
        json={"type": "payment", "data": {"id": "123"}},
    )
    assert response.status_code == 403
    get_settings.cache_clear()


def test_mercadopago_webhook_accepts_signature_in_production(
    client, production_webhook_env, monkeypatch
):
    monkeypatch.setenv("MERCADOPAGO_WEBHOOK_SECRET", "prod-mp-secret")
    get_settings.cache_clear()
    response = client.post(
        "/webhooks/mercadopago",
        headers={"x-signature": "prod-mp-secret"},
        json={"type": "payment", "data": {"id": "123"}},
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    get_settings.cache_clear()
