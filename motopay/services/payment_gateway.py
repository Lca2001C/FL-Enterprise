from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from motopay.domain.enums import PaymentGateway
from motopay.infrastructure.db.models import Cliente, Operacao
from motopay.infrastructure.payments.mercadopago_client import (
    MercadoPagoClient,
    mp_configured_for_operacao,
    mp_token_for_operacao,
)


@dataclass
class PixPaymentResult:
    payment_id: str
    status: str
    pix_copia_cola: str | None
    invoice_url: str | None = None


def _synthetic_pix(*, contrato_id: int, valor_total: Decimal) -> PixPaymentResult:
    cents = int(valor_total * 100)
    return PixPaymentResult(
        payment_id=f"demo_pay_{contrato_id}_{cents}",
        status="PENDING",
        pix_copia_cola=(
            f"00020101021226870014br.gov.bcb.pix2565demo/p/v2/OVERDUE_{contrato_id}_{cents}_BR5913MOTOPAY"
        ),
        invoice_url=None,
    )


def create_pix_for_contrato(
    *,
    op: Operacao,
    cliente: Cliente,
    contrato_id: int,
    valor_total: Decimal,
    due_date: date,
) -> tuple[str, str | None, str]:
    """Retorna (external_payment_id, pix_copia_cola, gateway)."""
    del due_date
    if mp_configured_for_operacao(op):
        pay = MercadoPagoClient(access_token=mp_token_for_operacao(op)).create_pix_payment(
            external_reference=f"contrato-{contrato_id}",
            value=valor_total,
            description=f"Contrato #{contrato_id}",
            payer_email=f"cliente{cliente.id}@motopay.local",
        )
        return pay.payment_id, pay.pix_copia_cola, PaymentGateway.MERCADOPAGO.value
    pay = _synthetic_pix(contrato_id=contrato_id, valor_total=valor_total)
    return pay.payment_id, pay.pix_copia_cola, PaymentGateway.MERCADOPAGO.value


def cancel_external_payment(*, gateway: str, payment_id: str | None, op: Operacao | None) -> None:
    """Pix Mercado Pago: novo código substitui o anterior no banco; cancelamento externo é best-effort."""
    del gateway, payment_id, op
