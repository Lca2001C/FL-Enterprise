from __future__ import annotations

import functools
from typing import Any

import mercadopago
from mercadopago.config import RequestOptions

__all__ = [
    "MercadoPagoApiError",
    "RequestOptions",
    "get_mercadopago_sdk",
    "raise_for_sdk_error",
]


class MercadoPagoApiError(Exception):
    """Erro retornado pelo SDK oficial do Mercado Pago (status HTTP não 2xx)."""

    def __init__(self, status: int, message: str, *, response: Any = None) -> None:
        self.status = status
        self.response = response
        super().__init__(message)


@functools.lru_cache(maxsize=8)
def get_mercadopago_sdk(access_token: str) -> mercadopago.SDK:
    return mercadopago.SDK(access_token)


def raise_for_sdk_error(result: dict[str, Any]) -> None:
    status = int(result.get("status") or 0)
    if 200 <= status < 300:
        return
    response = result.get("response")
    message = ""
    if isinstance(response, dict):
        message = str(response.get("message") or response.get("error") or "")
        if not message:
            cause = response.get("cause")
            if cause:
                message = str(cause)
    if not message:
        message = f"Mercado Pago API error (status {status})"
    raise MercadoPagoApiError(status, message, response=response)
