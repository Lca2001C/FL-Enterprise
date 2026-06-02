from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

_ORDER_PAID_STATUSES = frozenset({"processed"})


@dataclass
class ThreeDsInfo:
    external_resource_url: str | None
    creq: str | None


@dataclass
class MercadoPagoOrderResult:
    order_id: str
    payment_id: str
    order_status: str
    payment_status: str
    status_detail: str
    pix_copia_cola: str | None
    three_ds_info: ThreeDsInfo | None
    requires_3ds: bool

    @property
    def is_paid(self) -> bool:
        return (
            self.order_status in _ORDER_PAID_STATUSES
            or self.payment_status in _ORDER_PAID_STATUSES
        )


def normalize_webhook_data_id(data_id: str) -> str:
    """Orders API: manifest HMAC uses data.id in lowercase."""
    value = str(data_id).strip()
    if value.upper().startswith("ORD"):
        return value.lower()
    return value


def _first_payment(data: dict[str, Any]) -> dict[str, Any]:
    transactions = data.get("transactions") or {}
    payments = transactions.get("payments")
    if payments is None:
        return {}
    if isinstance(payments, list):
        return payments[0] if payments else {}
    if isinstance(payments, dict):
        return payments
    return {}


def _parse_three_ds(payment: dict[str, Any], order: dict[str, Any]) -> ThreeDsInfo | None:
    pm = payment.get("payment_method") or {}
    url = pm.get("url") or pm.get("external_resource_url")
    creq = pm.get("creq")
    if not url:
        sec = pm.get("transaction_security") or {}
        url = sec.get("url") or sec.get("external_resource_url")
        creq = creq or sec.get("creq")
    status_detail = str(payment.get("status_detail") or order.get("status_detail") or "")
    if url or status_detail == "pending_challenge":
        return ThreeDsInfo(
            external_resource_url=str(url) if url else None,
            creq=str(creq) if creq else None,
        )
    return None


def parse_order_response(data: dict[str, Any]) -> MercadoPagoOrderResult:
    payment = _first_payment(data)
    pm = payment.get("payment_method") or {}
    order_status = str(data.get("status", ""))
    payment_status = str(payment.get("status", ""))
    status_detail = str(payment.get("status_detail") or data.get("status_detail", ""))
    pix_code = pm.get("qr_code")
    three_ds = _parse_three_ds(payment, data)
    requires_3ds = status_detail == "pending_challenge" or bool(
        three_ds and three_ds.external_resource_url
    )
    payment_id = str(payment.get("id") or "")
    return MercadoPagoOrderResult(
        order_id=str(data.get("id", "")),
        payment_id=payment_id,
        order_status=order_status,
        payment_status=payment_status,
        status_detail=status_detail,
        pix_copia_cola=str(pix_code) if pix_code else None,
        three_ds_info=three_ds if requires_3ds else None,
        requires_3ds=requires_3ds,
    )


def is_order_paid(data: dict[str, Any]) -> bool:
    order_status = str(data.get("status", "")).lower()
    if order_status in _ORDER_PAID_STATUSES:
        return True
    payment = _first_payment(data)
    return str(payment.get("status", "")).lower() in _ORDER_PAID_STATUSES


def order_total_amount(data: dict[str, Any]) -> Decimal | None:
    raw = data.get("total_amount") or data.get("total_paid_amount")
    if raw is None:
        payment = _first_payment(data)
        raw = payment.get("amount") or payment.get("paid_amount")
    if raw is None:
        return None
    return Decimal(str(raw))
