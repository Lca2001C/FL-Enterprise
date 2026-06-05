from __future__ import annotations

from motopay.config import get_settings
from motopay.infrastructure.payments.mercadopago_client import (
    build_webhook_manifest,
    compute_webhook_signature,
    payer_email_for_mercadopago,
    verify_webhook_signature,
)
from motopay.infrastructure.payments.order_utils import normalize_webhook_data_id


def _signature_headers(
    *,
    secret: str,
    data_id: str,
    request_id: str = "req-test-1",
    ts: str = "1704908010",
) -> dict[str, str]:
    manifest_id = normalize_webhook_data_id(data_id)
    manifest = build_webhook_manifest(data_id=manifest_id, request_id=request_id, ts=ts)
    v1 = compute_webhook_signature(manifest=manifest, secret=secret)
    return {
        "x-signature": f"ts={ts},v1={v1}",
        "x-request-id": request_id,
    }


def test_verify_webhook_signature_valid():
    secret = "mp-webhook-secret"
    headers = _signature_headers(secret=secret, data_id="12345")
    assert verify_webhook_signature(
        secret=secret,
        x_signature=headers["x-signature"],
        x_request_id=headers["x-request-id"],
        data_id="12345",
    )


def test_payer_email_sandbox(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("MERCADOPAGO_CREDENTIALS_MODE", "test")
    monkeypatch.setenv("MERCADOPAGO_ACCESS_TOKEN_TEST", "tok")
    get_settings.cache_clear()
    assert payer_email_for_mercadopago(3) == "test_user_3@testuser.com"
    get_settings.cache_clear()


def test_payer_email_production_uses_cliente_email(monkeypatch):
    from motopay.infrastructure.db.models import Cliente

    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("MERCADOPAGO_CREDENTIALS_MODE", "production")
    monkeypatch.setenv("MERCADOPAGO_ACCESS_TOKEN", "tok")
    get_settings.cache_clear()
    cl = Cliente(
        id=5,
        operacao_id=1,
        nome="João",
        cpf="123",
        telefone="11999999999",
        email="joao@example.com",
    )
    assert payer_email_for_mercadopago(cl) == "joao@example.com"
    get_settings.cache_clear()
