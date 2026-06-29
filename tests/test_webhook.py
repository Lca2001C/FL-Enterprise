from __future__ import annotations

from unittest.mock import patch

from motopay.config import get_settings
from tests.test_mercadopago_client import _signature_headers

from tests.test_mercadopago_client import _signature_headers


def test_mercadopago_webhook_rejects_invalid_signature(client, monkeypatch):
    monkeypatch.setenv("MERCADOPAGO_CREDENTIALS_MODE", "production")
    monkeypatch.setenv("MERCADOPAGO_WEBHOOK_SECRET", "mp-secret")
    monkeypatch.setenv("MERCADOPAGO_WEBHOOK_SECRET_TEST", "")
    get_settings.cache_clear()
    response = client.post(
        "/webhooks/mercadopago",
<<<<<<< HEAD
        headers={
            "x-signature": "ts=1704908010,v1=invalid",
            "x-request-id": "req-1",
        },
        json={"type": "payment", "data": {"id": "123"}},
=======
        headers={"x-signature": "ts=1,v1=wrong", "x-request-id": "req-1"},
        json={"type": "order", "data": {"id": "ORD01ABC"}},
>>>>>>> main
    )
    assert response.status_code == 403
    get_settings.cache_clear()


<<<<<<< HEAD
def test_mercadopago_webhook_accepts_valid_hmac_signature(client, monkeypatch):
=======
def test_mercadopago_webhook_accepts_valid_signature(client, monkeypatch):
    monkeypatch.setenv("MERCADOPAGO_CREDENTIALS_MODE", "production")
>>>>>>> main
    monkeypatch.setenv("MERCADOPAGO_WEBHOOK_SECRET", "mp-secret")
    monkeypatch.setenv("MERCADOPAGO_WEBHOOK_SECRET_TEST", "")
    get_settings.cache_clear()
<<<<<<< HEAD
    headers = _signature_headers(secret="mp-secret", data_id="123")
    response = client.post(
        "/webhooks/mercadopago",
        headers=headers,
        json={"type": "payment", "data": {"id": "123"}},
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True}
=======
    headers = _signature_headers(secret="mp-secret", data_id="ORD01ABC")
    with patch("motopay.interfaces.api.routers.webhooks.MercadoPagoClient") as mock_cls:
        mock_cls.return_value.get_order.return_value = {"status": "pending"}
        response = client.post(
            "/webhooks/mercadopago",
            headers=headers,
            json={"type": "order", "data": {"id": "ORD01ABC"}},
        )
    assert response.status_code in (200, 502)
>>>>>>> main
    get_settings.cache_clear()


def test_mercadopago_webhook_without_secret(client, monkeypatch):
    monkeypatch.setenv("MERCADOPAGO_WEBHOOK_SECRET", "")
    monkeypatch.setenv("MERCADOPAGO_WEBHOOK_SECRET_TEST", "")
    get_settings.cache_clear()
    with patch("motopay.interfaces.api.routers.webhooks.MercadoPagoClient") as mock_cls:
        mock_cls.return_value.get_payment.return_value = {"status": "pending"}
        response = client.post(
            "/webhooks/mercadopago",
            json={"type": "payment", "data": {"id": "123"}},
        )
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    get_settings.cache_clear()
