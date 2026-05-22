from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import httpx

from motopay.config import get_settings
from motopay.infrastructure.db.models import Operacao


@dataclass
class MercadoPagoPaymentResult:
    payment_id: str
    status: str
    pix_copia_cola: str | None
    init_point: str | None


class MercadoPagoClient:
    def __init__(self, *, access_token: str | None = None) -> None:
        token = (access_token or get_settings().mercadopago_access_token).strip()
        if not token:
            raise ValueError("MERCADOPAGO_ACCESS_TOKEN não configurado")
        self._token = token
        self._base = "https://api.mercadopago.com"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    def create_pix_payment(
        self,
        *,
        external_reference: str,
        value: Decimal,
        description: str,
        payer_email: str,
    ) -> MercadoPagoPaymentResult:
        payload: dict[str, Any] = {
            "transaction_amount": float(value),
            "description": description,
            "payment_method_id": "pix",
            "external_reference": external_reference,
            "payer": {"email": payer_email or "cliente@motopay.local"},
        }
        r = httpx.post(
            f"{self._base}/v1/payments", headers=self._headers(), json=payload, timeout=60.0
        )
        r.raise_for_status()
        data = r.json()
        poi = data.get("point_of_interaction") or {}
        tx = poi.get("transaction_data") or {}
        return MercadoPagoPaymentResult(
            payment_id=str(data["id"]),
            status=str(data.get("status", "")),
            pix_copia_cola=tx.get("qr_code") or tx.get("qr_code_base64"),
            init_point=tx.get("ticket_url"),
        )

    def get_payment(self, payment_id: str) -> dict[str, Any]:
        r = httpx.get(
            f"{self._base}/v1/payments/{payment_id}", headers=self._headers(), timeout=30.0
        )
        r.raise_for_status()
        return r.json()

    def create_preapproval(
        self,
        *,
        external_reference: str,
        value: Decimal,
        reason: str,
        payer_email: str,
    ) -> str:
        payload = {
            "reason": reason,
            "external_reference": external_reference,
            "auto_recurring": {
                "frequency": 1,
                "frequency_type": "months",
                "transaction_amount": float(value),
                "currency_id": "BRL",
            },
            "payer_email": payer_email or "cliente@motopay.local",
            "back_url": get_settings().api_public_base_url,
        }
        r = httpx.post(
            f"{self._base}/preapproval", headers=self._headers(), json=payload, timeout=60.0
        )
        r.raise_for_status()
        return str(r.json()["id"])


def mp_token_for_operacao(op: Operacao | None) -> str:
    if op and op.mercadopago_access_token:
        return op.mercadopago_access_token.strip()
    return get_settings().mercadopago_access_token.strip()


def mp_configured_for_operacao(op: Operacao | None) -> bool:
    return bool(mp_token_for_operacao(op))
