from __future__ import annotations

from motopay.config import get_settings
from tests.test_mercadopago_client import _signature_headers


def test_mercadopago_webhook_rejects_invalid_signature(client, monkeypatch):
    monkeypatch.setenv("MERCADOPAGO_WEBHOOK_SECRET", "mp-secret")
    get_settings.cache_clear()
    response = client.post(
        "/webhooks/mercadopago",
        headers={
            "x-signature": "ts=1704908010,v1=invalid",
            "x-request-id": "req-1",
        },
        json={"type": "payment", "data": {"id": "123"}},
    )
    assert response.status_code == 403
    get_settings.cache_clear()


def test_mercadopago_webhook_accepts_valid_hmac_signature(client, monkeypatch):
    monkeypatch.setenv("MERCADOPAGO_WEBHOOK_SECRET", "mp-secret")
    get_settings.cache_clear()
    headers = _signature_headers(secret="mp-secret", data_id="123")
    response = client.post(
        "/webhooks/mercadopago",
        headers=headers,
        json={"type": "payment", "data": {"id": "123"}},
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    get_settings.cache_clear()


def test_mercadopago_webhook_without_secret(client, monkeypatch):
    monkeypatch.setenv("MERCADOPAGO_WEBHOOK_SECRET", "")
    get_settings.cache_clear()
    response = client.post(
        "/webhooks/mercadopago",
        json={"type": "payment", "data": {"id": "123"}},
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    get_settings.cache_clear()
