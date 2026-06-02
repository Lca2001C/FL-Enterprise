from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from motopay.infrastructure.payments.mercadopago_client import MercadoPagoClient


def test_create_online_order_card_credit(monkeypatch: pytest.MonkeyPatch):
    captured: dict = {}

    def fake_create(payload, request_options):
        captured["payload"] = payload
        return {
            "status": 201,
            "response": {
                "id": "ORDCARD1",
                "status": "processed",
                "transactions": {
                    "payments": [
                        {
                            "id": "PAYCARD1",
                            "status": "processed",
                            "status_detail": "accredited",
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
        result = MercadoPagoClient(access_token="tok").create_online_order(
            external_reference="cobranca-1",
            value=Decimal("24.50"),
            payer_email="test@test.com",
            payment_kind="credit_card",
            payment_method_id="master",
            token="tok123",
            installments=1,
        )

    pm = captured["payload"]["transactions"]["payments"][0]["payment_method"]
    assert pm["type"] == "credit_card"
    assert pm["token"] == "tok123"
    assert result.is_paid


def test_create_online_order_parses_pending_challenge_3ds():
    def fake_create(payload, request_options):
        return {
            "status": 201,
            "response": {
                "id": "ORD3DS",
                "status": "action_required",
                "status_detail": "pending_challenge",
                "transactions": {
                    "payments": [
                        {
                            "id": "PAY3DS",
                            "status": "action_required",
                            "status_detail": "pending_challenge",
                            "payment_method": {"url": "https://challenge.example"},
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
        result = MercadoPagoClient(access_token="tok").create_online_order(
            external_reference="cob-2",
            value=Decimal("10"),
            payer_email="a@b.com",
            payment_kind="debit_card",
            payment_method_id="debvisa",
            token="tok",
            installments=1,
        )

    assert result.requires_3ds
    assert result.three_ds_info is not None
    assert result.three_ds_info.external_resource_url == "https://challenge.example"
