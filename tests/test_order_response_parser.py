from __future__ import annotations

from motopay.infrastructure.payments.order_utils import (
    is_order_paid,
    normalize_webhook_data_id,
    order_total_amount,
    parse_order_response,
)


def test_parse_pix_waiting_transfer():
    data = {
        "id": "ORD01HRYFWNYRE1MR1E60MW3X0T2P",
        "status": "action_required",
        "status_detail": "waiting_transfer",
        "transactions": {
            "payments": [
                {
                    "id": "PAY01HRYFXQ53Q3JPEC48MYWMR0TE",
                    "status": "action_required",
                    "status_detail": "waiting_transfer",
                    "payment_method": {
                        "id": "pix",
                        "type": "bank_transfer",
                        "qr_code": "00020126580014br.gov.bcb.pix",
                    },
                }
            ]
        },
    }
    result = parse_order_response(data)
    assert result.order_id == "ORD01HRYFWNYRE1MR1E60MW3X0T2P"
    assert result.payment_id == "PAY01HRYFXQ53Q3JPEC48MYWMR0TE"
    assert result.pix_copia_cola == "00020126580014br.gov.bcb.pix"
    assert not result.is_paid


def test_parse_card_processed():
    data = {
        "id": "ORD01JQ4S4KY8HWQ6NA5PXB65B3D3",
        "status": "processed",
        "total_amount": "100.00",
        "transactions": {
            "payments": [
                {
                    "id": "PAY01JQ4S4KY8HWQ6NA5PXB65B3D4",
                    "status": "processed",
                    "status_detail": "accredited",
                }
            ]
        },
    }
    result = parse_order_response(data)
    assert result.is_paid
    assert is_order_paid(data)
    assert order_total_amount(data) == 100


def test_parse_pending_challenge_3ds():
    data = {
        "id": "ORD3DS",
        "status": "action_required",
        "status_detail": "pending_challenge",
        "transactions": {
            "payments": [
                {
                    "id": "PAY3DS",
                    "status": "action_required",
                    "status_detail": "pending_challenge",
                    "payment_method": {
                        "url": "https://mp.example/challenge",
                    },
                }
            ]
        },
    }
    result = parse_order_response(data)
    assert result.requires_3ds
    assert result.three_ds_info is not None
    assert result.three_ds_info.external_resource_url == "https://mp.example/challenge"


def test_normalize_webhook_data_id_lowercase_order():
    assert normalize_webhook_data_id("ORD01ABC") == "ord01abc"
    assert normalize_webhook_data_id("12345") == "12345"
