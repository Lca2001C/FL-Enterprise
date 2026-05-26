from __future__ import annotations

import pytest
from motopay.config import get_settings


@pytest.fixture
def production_webhook_env(monkeypatch: pytest.MonkeyPatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET", "x" + "a" * 48)
    monkeypatch.setenv("ASAAS_WEBHOOK_TOKEN", "prod-webhook-token")
    monkeypatch.setenv("ASAAS_API_KEY", "k")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("ASAAS_API_BASE_URL", "https://api.asaas.com/api/v3")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pw@prod-db.example:5432/motopay")
    monkeypatch.setenv("REDIS_URL", "rediss://:strong-redis-secret@redis.example:6380/0")
    monkeypatch.setenv("CORS_ORIGINS", "https://admin.example.test")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_webhook_rejects_query_token_in_production(client, production_webhook_env):
    token = get_settings().asaas_webhook_token
    response = client.post(
        f"/webhooks/asaas?token={token}",
        json={"event": "PAYMENT_CONFIRMED", "payment": {}},
    )
    assert response.status_code == 403
    assert "X-Webhook-Token" in response.json()["detail"]


def test_webhook_accepts_header_in_production(client, production_webhook_env):
    token = get_settings().asaas_webhook_token
    response = client.post(
        "/webhooks/asaas",
        headers={"X-Webhook-Token": token},
        json={"event": "PAYMENT_CONFIRMED", "payment": {}},
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True}
