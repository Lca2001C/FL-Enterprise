from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from motopay.config import get_settings
from motopay.infrastructure.payments.mercadopago_client import (
    MercadoPagoClient,
    build_webhook_manifest,
    compute_webhook_signature,
    verify_webhook_signature,
)
from motopay.infrastructure.payments.mercadopago_sdk import MercadoPagoApiError
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


def test_verify_webhook_signature_order_id_lowercase():
    secret = "mp-webhook-secret"
    headers = _signature_headers(secret=secret, data_id="ORD01ABC")
    assert verify_webhook_signature(
        secret=secret,
        x_signature=headers["x-signature"],
        x_request_id=headers["x-request-id"],
        data_id="ORD01ABC",
    )


def test_verify_webhook_signature_rejects_tampered_id():
    secret = "mp-webhook-secret"
    headers = _signature_headers(secret=secret, data_id="12345")
    assert not verify_webhook_signature(
        secret=secret,
        x_signature=headers["x-signature"],
        x_request_id=headers["x-request-id"],
        data_id="99999",
    )


def test_create_online_order_pix(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("MERCADOPAGO_ACCESS_TOKEN", "test-token")
    get_settings.cache_clear()

    captured: dict = {}

    def fake_create(payload, request_options):
        captured["payload"] = payload
        captured["request_options"] = request_options
        return {
            "status": 201,
            "response": {
                "id": "ORD01TEST",
                "status": "action_required",
                "status_detail": "waiting_transfer",
                "transactions": {
                    "payments": [
                        {
                            "id": "PAY01TEST",
                            "status": "action_required",
                            "payment_method": {"qr_code": "00020126pix"},
                        }
                    ]
                },
            },
        }

    mock_order = MagicMock()
    mock_order.create.side_effect = fake_create
    mock_sdk = MagicMock()
    mock_sdk.order.return_value = mock_order

    with patch(
        "motopay.infrastructure.payments.mercadopago_client.get_mercadopago_sdk",
        return_value=mock_sdk,
    ):
        result = MercadoPagoClient().create_online_order(
            external_reference="cobranca-1",
            value=Decimal("100.00"),
            payer_email="a@b.com",
            payer_cpf="12345678901",
            payment_kind="pix",
            pix_due_date=date(2026, 6, 15),
        )

    assert result.order_id == "ORD01TEST"
    assert result.payment_id == "PAY01TEST"
    assert result.pix_copia_cola == "00020126pix"
    assert captured["payload"]["type"] == "online"
    assert captured["payload"]["processing_mode"] == "automatic"
    assert captured["payload"]["transactions"]["payments"][0]["payment_method"]["id"] == "pix"
    assert "expiration_time" in captured["payload"]["transactions"]["payments"][0]
    headers = captured["request_options"].custom_headers
    assert "x-idempotency-key" in headers
    get_settings.cache_clear()


def test_get_order_raises_on_sdk_error():
    mock_order = MagicMock()
    mock_order.get.return_value = {"status": 404, "response": {"message": "not found"}}
    mock_sdk = MagicMock()
    mock_sdk.order.return_value = mock_order

    with patch(
        "motopay.infrastructure.payments.mercadopago_client.get_mercadopago_sdk",
        return_value=mock_sdk,
    ):
        with pytest.raises(MercadoPagoApiError):
            MercadoPagoClient(access_token="tok").get_order("ORDmissing")
