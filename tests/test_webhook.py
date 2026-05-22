from __future__ import annotations

from motopay.config import get_settings


def test_webhook_rejects_invalid_token(client):
    response = client.post(
        "/webhooks/asaas?token=wrong",
        json={"event": "PAYMENT_CONFIRMED", "payment": {"id": "pay_123"}},
    )
    assert response.status_code == 403


def test_webhook_accepts_valid_token_in_header(client):
    token = get_settings().asaas_webhook_token
    response = client.post(
        "/webhooks/asaas",
        headers={"X-Webhook-Token": token},
        json={"event": "PAYMENT_CONFIRMED", "payment": {}},
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_webhook_accepts_valid_token_in_query(client):
    token = get_settings().asaas_webhook_token
    response = client.post(
        f"/webhooks/asaas?token={token}",
        json={"event": "PAYMENT_CONFIRMED", "payment": {}},
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True}
