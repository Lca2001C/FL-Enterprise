from __future__ import annotations

from unittest.mock import patch

from motopay.infrastructure.payments import mercadopago_sdk


def test_get_mercadopago_sdk_caches_by_token():
    mercadopago_sdk.get_mercadopago_sdk.cache_clear()
    with patch("motopay.infrastructure.payments.mercadopago_sdk.mercadopago.SDK") as mock_sdk_cls:
        mock_sdk_cls.side_effect = lambda token: f"sdk:{token}"
        a = mercadopago_sdk.get_mercadopago_sdk("token-a")
        b = mercadopago_sdk.get_mercadopago_sdk("token-a")
        c = mercadopago_sdk.get_mercadopago_sdk("token-b")
    assert a is b
    assert a != c
    assert mock_sdk_cls.call_count == 2
    mercadopago_sdk.get_mercadopago_sdk.cache_clear()


def test_raise_for_sdk_error_accepts_2xx():
    mercadopago_sdk.raise_for_sdk_error({"status": 201, "response": {}})


def test_raise_for_sdk_error_raises_on_4xx():
    import pytest

    from motopay.infrastructure.payments.mercadopago_sdk import MercadoPagoApiError

    with pytest.raises(MercadoPagoApiError) as exc_info:
        mercadopago_sdk.raise_for_sdk_error(
            {"status": 400, "response": {"message": "bad request"}}
        )
    assert exc_info.value.status == 400
    assert "bad request" in str(exc_info.value)
