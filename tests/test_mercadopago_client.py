from __future__ import annotations

from decimal import Decimal

from motopay.config import get_settings
from motopay.infrastructure.payments.mercadopago_client import (
    MercadoPagoApiError,
    MercadoPagoClient,
    _order_data_from_mp_error,
    build_webhook_manifest,
    compute_webhook_signature,
    mercadopago_api_error_message,
    mercadopago_status_detail_message,
    payer_email_for_mercadopago,
    verify_webhook_signature,
)
from motopay.infrastructure.payments.order_utils import normalize_webhook_data_id, parse_order_response


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


def test_mercadopago_status_detail_rejected_by_issuer():
    msg = mercadopago_status_detail_message("rejected_by_issuer")
    assert "recusado" in msg.lower()
    assert "sandbox" in msg.lower()


def test_order_data_from_mp_402_error():
    body = {
        "errors": [{"details": ["PAY01: rejected_by_issuer"]}],
        "data": {"id": "ORD01TEST", "status": "failed"},
    }
    exc = MercadoPagoApiError(402, "failed", body)
    assert _order_data_from_mp_error(exc) == body["data"]


def test_mercadopago_api_error_message_parses_orders_402():
    body = {
        "errors": [{"message": "The following transactions failed", "details": ["x: rejected_by_issuer"]}],
        "data": {"id": "ORD01", "status": "failed"},
    }
    exc = MercadoPagoApiError(402, "failed", body)
    msg = mercadopago_api_error_message(exc)
    assert "recusado" in msg.lower()


def test_mercadopago_api_error_message_invalid_token_length():
    body = {
        "errors": [
            {
                "code": "property_value",
                "message": "Invalid value for property",
                "details": [
                    "'$.transactions.payments[0].payment_method.token' - length must be >= 32, but got 4"
                ],
            }
        ],
    }
    exc = MercadoPagoApiError(400, "bad request", body)
    msg = mercadopago_api_error_message(exc)
    assert "token" in msg.lower() or "cvv" in msg.lower()


def test_create_saved_card_payment_token(monkeypatch):
    def fake_request(self, method, path, **kwargs):
        assert method == "POST"
        assert path == "/v1/card_tokens"
        assert kwargs["json"]["security_code"] == "1234"
        return {"id": "a" * 32}

    monkeypatch.setattr(MercadoPagoClient, "_request", fake_request)
    client = MercadoPagoClient(access_token="test-token")
    token = client.create_saved_card_payment_token(
        customer_id="cust-1",
        card_id="card-1",
        security_code="1234",
    )
    assert len(token) == 32


def test_create_order_refund_full(monkeypatch):
    calls: list[tuple[str, str, dict]] = []

    def fake_request(self, method, path, **kwargs):
        calls.append((method, path, kwargs.get("json") or {}))
        return {"id": "ORD01", "status": "refunded"}

    monkeypatch.setattr(MercadoPagoClient, "_request", fake_request)
    client = MercadoPagoClient(access_token="test-token")
    data = client.create_order_refund("ORD01TEST")
    assert data["status"] == "refunded"
    assert calls[0] == ("POST", "/v1/orders/ORD01TEST/refund", {})


def test_create_order_refund_partial(monkeypatch):
    def fake_request(self, method, path, **kwargs):
        body = kwargs.get("json") or {}
        assert body["transactions"][0]["id"] == "PAY01ABC"
        assert body["transactions"][0]["amount"] == "50.00"
        return {"id": "ORD01", "status": "processed", "status_detail": "partially_refunded"}

    monkeypatch.setattr(MercadoPagoClient, "_request", fake_request)
    client = MercadoPagoClient(access_token="test-token")
    client.create_order_refund(
        "ORD01TEST",
        payment_id="PAY01ABC",
        amount=Decimal("50"),
    )


def test_create_refund_routes_orders_api(monkeypatch):
    def fake_order_refund(self, order_id, *, payment_id=None, amount=None):
        assert order_id == "ORD01"
        assert payment_id == "PAY01XYZ"
        return {"ok": True}

    monkeypatch.setattr(MercadoPagoClient, "create_order_refund", fake_order_refund)
    client = MercadoPagoClient(access_token="test-token")
    assert client.create_refund("PAY01XYZ", amount=Decimal("10"), order_id="ORD01") == {"ok": True}


def test_create_online_order_parses_402_with_order_data(monkeypatch):
    order_payload = {
        "id": "ORD01TEST",
        "status": "failed",
        "status_detail": "failed",
        "transactions": {
            "payments": [
                {
                    "id": "PAY01",
                    "status": "failed",
                    "status_detail": "rejected_by_issuer",
                }
            ]
        },
    }

    def fake_request(self, method, path, **kwargs):
        raise MercadoPagoApiError(
            402,
            "failed",
            {"errors": [{"details": ["PAY01: rejected_by_issuer"]}], "data": order_payload},
        )

    monkeypatch.setattr(MercadoPagoClient, "_request", fake_request)
    client = MercadoPagoClient(access_token="test-token")
    result = client.create_online_order(
        external_reference="cob-1",
        value=Decimal("100"),
        payer_email="test@test.com",
        payment_method_id="visa",
        payment_method_type="credit_card",
        token="tok",
    )
    parsed = parse_order_response(order_payload)
    assert result.order_id == parsed.order_id
    assert result.status_detail == "rejected_by_issuer"
    assert not result.is_paid


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
