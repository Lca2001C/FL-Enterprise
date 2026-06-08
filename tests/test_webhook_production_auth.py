from __future__ import annotations

from unittest.mock import patch

import pytest
from motopay.config import get_settings

from tests.test_mercadopago_client import _signature_headers


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
    headers = _signature_headers(secret="prod-mp-secret", data_id="123")
    with patch("motopay.interfaces.api.routers.webhooks.MercadoPagoClient") as mock_cls:
        mock_cls.return_value.get_payment.return_value = {"status": "pending"}
        response = client.post(
            "/webhooks/mercadopago",
            headers=headers,
            json={"type": "payment", "data": {"id": "123"}},
        )
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    get_settings.cache_clear()
