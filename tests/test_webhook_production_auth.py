from __future__ import annotations

import pytest
from motopay.config import get_settings
from tests.test_mercadopago_client import _signature_headers

from tests.conftest import apply_base_production_env
from tests.test_mercadopago_client import _signature_headers


@pytest.fixture
def production_webhook_env(monkeypatch: pytest.MonkeyPatch) -> None:
    get_settings.cache_clear()
    apply_base_production_env(monkeypatch)
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
        headers={
            "x-signature": "ts=1704908010,v1=bad",
            "x-request-id": "req-prod",
        },
        json={"type": "payment", "data": {"id": "123"}},
    )
    assert response.status_code == 403
    get_settings.cache_clear()


def test_mercadopago_webhook_rejects_unsigned_when_secret_missing_in_production(
    client, production_webhook_env, monkeypatch
):
    # Fail-closed: sem MERCADOPAGO_WEBHOOK_SECRET configurado, produção deve
    # recusar o webhook em vez de aceitar qualquer requisição não assinada.
    # ALLOW_PRODUCTION_WITHOUT_MERCADOPAGO permite Settings() subir sem o secret
    # (deploy temporário); o endpoint de webhook ainda rejeita em runtime.
    monkeypatch.setenv("ALLOW_PRODUCTION_WITHOUT_MERCADOPAGO", "true")
    monkeypatch.setenv("MERCADOPAGO_WEBHOOK_SECRET", "")
    get_settings.cache_clear()
    response = client.post(
        "/webhooks/mercadopago",
        json={"type": "payment", "data": {"id": "123"}},
    )
    assert response.status_code == 403
    get_settings.cache_clear()


def test_mercadopago_webhook_accepts_signature_in_production(
    client, production_webhook_env, monkeypatch
):
    monkeypatch.setenv("MERCADOPAGO_WEBHOOK_SECRET", "prod-mp-secret")
    get_settings.cache_clear()
<<<<<<< HEAD
    headers = _signature_headers(secret="prod-mp-secret", data_id="123", request_id="req-prod")
    response = client.post(
        "/webhooks/mercadopago",
        headers=headers,
        json={"type": "payment", "data": {"id": "123"}},
    )
=======
    headers = _signature_headers(secret="prod-mp-secret", data_id="123")
    with patch("motopay.interfaces.api.routers.webhooks.MercadoPagoClient") as mock_cls:
        mock_cls.return_value.get_payment.return_value = {"status": "pending"}
        response = client.post(
            "/webhooks/mercadopago",
            headers=headers,
            json={"type": "payment", "data": {"id": "123"}},
        )
>>>>>>> main
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    get_settings.cache_clear()
