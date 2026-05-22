from __future__ import annotations

from datetime import date
from decimal import Decimal

from motopay.config import get_settings
from motopay.domain.enums import PaymentGateway, PaymentProvider
from motopay.infrastructure.db.models import Cliente, Operacao
from motopay.infrastructure.payments.asaas_client import AsaasClient, AsaasPaymentResult
from motopay.infrastructure.payments.mercadopago_client import (
    MercadoPagoClient,
    mp_configured_for_operacao,
    mp_token_for_operacao,
)


def provider_for_operacao(op: Operacao | None) -> str:
    if op and op.payment_provider:
        return op.payment_provider
    return PaymentProvider.ASAAS.value


def _asaas_configured() -> bool:
    return bool(get_settings().asaas_api_key.strip())


def _synthetic_pix(*, contrato_id: int, valor_total: Decimal) -> AsaasPaymentResult:
    cents = int(valor_total * 100)
    return AsaasPaymentResult(
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
    asaas_customer_id: str,
) -> tuple[str, str | None, str]:
    """Retorna (external_payment_id, pix_copia_cola, gateway)."""
    provider = provider_for_operacao(op)
    if provider == PaymentProvider.MERCADOPAGO.value:
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

    if _asaas_configured():
        pay = AsaasClient().create_pix_payment(
            customer_id=asaas_customer_id,
            value=valor_total,
            due_date=due_date.isoformat(),
            description=f"Contrato #{contrato_id} — locação moto",
        )
        return pay.payment_id, pay.pix_copia_cola, PaymentGateway.ASAAS.value
    pay = _synthetic_pix(contrato_id=contrato_id, valor_total=valor_total)
    return pay.payment_id, pay.pix_copia_cola, PaymentGateway.ASAAS.value


def cancel_external_payment(*, gateway: str, payment_id: str | None, op: Operacao | None) -> None:
    if not payment_id:
        return
    if gateway == PaymentGateway.MERCADOPAGO.value:
        return
    if _asaas_configured():
        try:
            AsaasClient().cancel_payment(payment_id)
        except Exception:
            pass
