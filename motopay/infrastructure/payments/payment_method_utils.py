from __future__ import annotations

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
        return PaymentMethodType.DEBIT_CARD.value
    return PaymentMethodType.CREDIT_CARD.value


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
