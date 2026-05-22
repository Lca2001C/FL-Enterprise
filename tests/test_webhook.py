from __future__ import annotations


def test_webhook_rejects_invalid_token(client):
    response = client.post(
        "/webhooks/asaas?token=wrong",
        json={"event": "PAYMENT_CONFIRMED", "payment": {"id": "pay_123"}},
    )
    assert response.status_code == 403


def test_webhook_accepts_valid_token_in_header(client):
    response = client.post(
        "/webhooks/asaas",
        headers={"X-Webhook-Token": "test-webhook-token"},
        json={"event": "PAYMENT_CONFIRMED", "payment": {}},
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_webhook_accepts_valid_token_in_query(client):
    response = client.post(
        "/webhooks/asaas?token=test-webhook-token",
        json={"event": "PAYMENT_CONFIRMED", "payment": {}},
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True}
