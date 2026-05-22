from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import httpx

from motopay.config import get_settings


@dataclass
class AsaasPaymentResult:
    payment_id: str
    status: str
    pix_copia_cola: str | None
    invoice_url: str | None


class AsaasClient:
    def __init__(self) -> None:
        s = get_settings()
        self._base = s.asaas_api_base_url.rstrip("/")
        self._token = s.asaas_api_key

    def _headers(self) -> dict[str, str]:
        return {"access_token": self._token, "Content-Type": "application/json", "User-Agent": "MotoPayAdmin/0.1"}

    def create_customer(self, *, name: str, cpf_cnpj: str, phone: str | None) -> str:
        payload: dict[str, Any] = {"name": name, "cpfCnpj": "".join(c for c in cpf_cnpj if c.isdigit())}
        if phone:
            payload["mobilePhone"] = "".join(c for c in phone if c.isdigit())
        r = httpx.post(f"{self._base}/customers", headers=self._headers(), json=payload, timeout=60.0)
        r.raise_for_status()
        data = r.json()
        return str(data["id"])

    def create_subscription(
        self,
        *,
        customer_id: str,
        value: Decimal,
        cycle: str,
        description: str,
        next_due: str,
    ) -> str:
        """cycle: WEEKLY or MONTHLY for Asaas."""
        asaas_cycle = "WEEKLY" if cycle == "semanal" else "MONTHLY"
        payload = {
            "customer": customer_id,
            "billingType": "PIX",
            "value": float(value),
            "cycle": asaas_cycle,
            "description": description,
            "nextDueDate": next_due,
        }
        r = httpx.post(f"{self._base}/subscriptions", headers=self._headers(), json=payload, timeout=60.0)
        r.raise_for_status()
        return str(r.json()["id"])

    def create_pix_payment(self, *, customer_id: str, value: Decimal, due_date: str, description: str) -> AsaasPaymentResult:
        payload = {
            "customer": customer_id,
            "billingType": "PIX",
            "value": float(value),
            "dueDate": due_date,
            "description": description,
        }
        r = httpx.post(f"{self._base}/payments", headers=self._headers(), json=payload, timeout=60.0)
        r.raise_for_status()
        data = r.json()
        pix = data.get("pixCopiaECola") or data.get("pixCopyAndPaste")
        return AsaasPaymentResult(
            payment_id=str(data["id"]),
            status=str(data.get("status", "")),
            pix_copia_cola=str(pix) if pix else None,
            invoice_url=data.get("invoiceUrl"),
        )

    def get_payment(self, payment_id: str) -> dict[str, Any]:
        r = httpx.get(
            f"{self._base}/payments/{payment_id}",
            headers=self._headers(),
            timeout=30.0,
        )
        r.raise_for_status()
        return r.json()
