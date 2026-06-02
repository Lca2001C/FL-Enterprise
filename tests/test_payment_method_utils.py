import pytest

from motopay.domain.enums import PaymentMethodType
from motopay.infrastructure.payments.payment_method_utils import (
    installments_for_payment_method,
    is_debit_payment_method_id,
    resolve_payment_method_type,
)


@pytest.mark.parametrize(
    "pm_id,expected",
    [
        ("debvisa", True),
        ("debelo", True),
        ("master_debit", True),
        ("visa", False),
        ("master", False),
        ("credit_card", False),
    ],
)
def test_is_debit_payment_method_id(pm_id: str, expected: bool) -> None:
    assert is_debit_payment_method_id(pm_id) is expected


def test_resolve_explicit_kind() -> None:
    assert (
        resolve_payment_method_type("visa", explicit_kind=PaymentMethodType.DEBIT_CARD.value)
        == PaymentMethodType.DEBIT_CARD.value
    )
    assert (
        resolve_payment_method_type("debvisa", explicit_kind=PaymentMethodType.CREDIT_CARD.value)
        == PaymentMethodType.CREDIT_CARD.value
    )


def test_resolve_from_payment_method_id() -> None:
    assert resolve_payment_method_type("debmaster") == PaymentMethodType.DEBIT_CARD.value
    assert resolve_payment_method_type("visa") == PaymentMethodType.CREDIT_CARD.value


def test_installments_debit_forces_one() -> None:
    assert (
        installments_for_payment_method("visa", 12, explicit_kind=PaymentMethodType.DEBIT_CARD.value)
        == 1
    )
    assert installments_for_payment_method("debvisa", 6) == 1
    assert installments_for_payment_method("visa", 3) == 3
