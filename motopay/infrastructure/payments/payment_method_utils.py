from __future__ import annotations

<<<<<<< HEAD
from motopay.domain.enums import PaymentMethodType


def is_debit_payment_method_id(payment_method_id: str) -> bool:
    pm = payment_method_id.strip().lower()
    return pm.startswith("deb") or "debit" in pm


def resolve_payment_method_type(
    payment_method_id: str,
    *,
    explicit_kind: str | None = None,
) -> str:
    if explicit_kind in (
        PaymentMethodType.PIX.value,
        PaymentMethodType.CREDIT_CARD.value,
        PaymentMethodType.DEBIT_CARD.value,
    ):
        return explicit_kind
    if is_debit_payment_method_id(payment_method_id):
=======
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
>>>>>>> main
        return PaymentMethodType.DEBIT_CARD.value
    return PaymentMethodType.CREDIT_CARD.value


<<<<<<< HEAD
def installments_for_payment_method(
    payment_method_id: str,
    installments: int,
    *,
    explicit_kind: str | None = None,
) -> int:
    kind = resolve_payment_method_type(payment_method_id, explicit_kind=explicit_kind)
    if kind == PaymentMethodType.DEBIT_CARD.value:
        return 1
    return max(1, installments)
=======
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
>>>>>>> main
