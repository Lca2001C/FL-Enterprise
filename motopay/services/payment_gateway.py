from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from motopay.domain.enums import PaymentGateway
from motopay.domain.exceptions import ForbiddenError
from motopay.infrastructure.db.models import Cliente, Operacao
from motopay.infrastructure.payments.mercadopago_client import (
    MercadoPagoClient,
    mercadopago_api_error_message,
    mp_configured_for_operacao,
    mp_credentials_complete,
    mp_token_for_operacao,
    payer_email_for_mercadopago,
    uses_operacao_mercadopago_credentials,
)
from motopay.infrastructure.payments.mercadopago_sdk import MercadoPagoApiError


@dataclass
class PixOrderResult:
    order_id: str
    payment_id: str
    pix_copia_cola: str | None


def _synthetic_pix(*, cobranca_id: int, valor_total: Decimal) -> PixOrderResult:
    cents = int(valor_total * 100)
    return PixOrderResult(
        order_id=f"demo_ord_{cobranca_id}_{cents}",
        payment_id=f"demo_pay_{cobranca_id}_{cents}",
        pix_copia_cola=(
            f"00020101021226870014br.gov.bcb.pix2565demo/p/v2/COB_{cobranca_id}_{cents}_BR5913MOTOPAY"
        ),
    )


def create_pix_for_cobranca(
    *,
    op: Operacao,
    cliente: Cliente,
    cobranca_id: int,
    valor_total: Decimal,
    due_date: date,
) -> tuple[str, str, str | None, str]:
    """Retorna (order_id, payment_id, pix_copia_cola, gateway)."""
    external_ref = f"cobranca-{cobranca_id}"
    if mp_configured_for_operacao(op):
        if uses_operacao_mercadopago_credentials(op) and not mp_credentials_complete(op):
            raise RuntimeError(
                "Credenciais Mercado Pago incompletas para esta operação. "
                "Configure Access Token, Public Key e Webhook Secret em Ajustes."
            )
        try:
            order = MercadoPagoClient(access_token=mp_token_for_operacao(op)).create_online_order(
                external_reference=external_ref,
                value=valor_total,
                payer_email=payer_email_for_mercadopago(cliente.id),
                payer_cpf=cliente.cpf,
                payment_kind="pix",
                pix_due_date=due_date,
                idempotency_key=f"pix-{external_ref}",
            )
        except MercadoPagoApiError as exc:
            raise ForbiddenError(
                f"Falha ao criar Pix no Mercado Pago: {mercadopago_api_error_message(exc)}"
            ) from exc
        return (
            order.order_id,
            order.payment_id,
            order.pix_copia_cola,
            PaymentGateway.MERCADOPAGO.value,
        )
    pay = _synthetic_pix(cobranca_id=cobranca_id, valor_total=valor_total)
    return pay.order_id, pay.payment_id, pay.pix_copia_cola, PaymentGateway.MERCADOPAGO.value


def cancel_external_payment(
    *,
    gateway: str,
    order_id: str | None,
    op: Operacao | None,
) -> None:
    """Cancela order Pix pendente no MP (best-effort)."""
    if gateway != PaymentGateway.MERCADOPAGO.value or not order_id or not op:
        return
    if order_id.startswith("demo_"):
        return
    if not mp_configured_for_operacao(op):
        return
    try:
        MercadoPagoClient(access_token=mp_token_for_operacao(op)).cancel_order(order_id)
    except MercadoPagoApiError:
        pass
