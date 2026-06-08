from __future__ import annotations

from typing import Literal

from motopay.domain.enums import PaymentMethodType

_DEBIT_METHOD_IDS = frozenset({"debvisa", "debmaster", "debelo"})


def is_debit_payment_method_id(method_id: str) -> bool:
    return method_id.lower() in _DEBIT_METHOD_IDS or method_id.lower().startswith("deb")


def resolve_payment_method_type(
  method_id: str,
  explicit: PaymentMethodType | str | None = None,
) -> str:
    if explicit:
        return str(explicit.value if hasattr(explicit, "value") else explicit)
    if is_debit_payment_method_id(method_id):
        return PaymentMethodType.DEBIT_CARD.value
    return PaymentMethodType.CREDIT_CARD.value


def installments_for_payment_method(method_type: str) -> int:
    if method_type == PaymentMethodType.DEBIT_CARD.value:
        return 1
    return 1


def mp_payment_method_type(
    kind: Literal["pix", "credit_card", "debit_card"],
) -> Literal["bank_transfer", "credit_card", "debit_card"]:
    if kind == "pix":
        return "bank_transfer"
    if kind == "debit_card":
        return "debit_card"
    return "credit_card"
