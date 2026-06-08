from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from motopay.domain.enums import PaymentGateway, PaymentMethodType
from motopay.domain.exceptions import ForbiddenError
from sqlalchemy.orm import Session

from motopay.infrastructure.db.models import Cliente, Operacao
from motopay.services.mercadopago_token_service import ensure_valid_mp_token
from motopay.infrastructure.payments.mercadopago_client import (
    MercadoPagoApiError,
    MercadoPagoClient,
    assert_payer_email_ready,
    mercadopago_api_error_message,
    mp_configured_for_operacao,
    mp_credentials_complete,
    mp_token_for_operacao,
    payer_email_for_mercadopago,
)


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


def _access_token(db: Session | None, op: Operacao) -> str:
    if db is not None:
        return ensure_valid_mp_token(db, op)
    return mp_token_for_operacao(op)


def create_pix_for_cobranca(
    *,
    op: Operacao,
    cliente: Cliente,
    cobranca_id: int,
    valor_total: Decimal,
    due_date: date,
    db: Session | None = None,
) -> tuple[str, str, str | None, str]:
    """Retorna (order_id, payment_id, pix_copia_cola, gateway)."""
    del due_date
    if not mp_credentials_complete(op):
        if mp_configured_for_operacao(op):
            raise ForbiddenError(
                "Credenciais Mercado Pago incompletas. Configure Access Token, Public Key e "
                "Webhook Secret em Ajustes."
            )
    if mp_configured_for_operacao(op) and mp_credentials_complete(op):
        assert_payer_email_ready(cliente)
        try:
            order = MercadoPagoClient(access_token=_access_token(db, op)).create_online_order(
                external_reference=f"cobranca-{cobranca_id}",
                value=valor_total,
                payer_email=payer_email_for_mercadopago(cliente),
                payer_cpf=cliente.cpf,
                payment_method_id="pix",
                payment_method_type="bank_transfer",
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


def create_pix_for_contrato(
    *,
    op: Operacao,
    cliente: Cliente,
    contrato_id: int,
    valor_total: Decimal,
    due_date: date,
    db: Session | None = None,
) -> tuple[str, str, str | None, str]:
    """Compat: Pix por contrato (usa cobranca-{contrato_id} como referência externa)."""
    del due_date
    if mp_configured_for_operacao(op) and mp_credentials_complete(op):
        assert_payer_email_ready(cliente)
        try:
            order = MercadoPagoClient(access_token=_access_token(db, op)).create_online_order(
                external_reference=f"contrato-{contrato_id}",
                value=valor_total,
                payer_email=payer_email_for_mercadopago(cliente),
                payer_cpf=cliente.cpf,
                payment_method_id="pix",
                payment_method_type="bank_transfer",
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
    pay = _synthetic_pix(cobranca_id=contrato_id, valor_total=valor_total)
    return pay.order_id, pay.payment_id, pay.pix_copia_cola, PaymentGateway.MERCADOPAGO.value


def cancel_external_payment(
    *,
    gateway: str,
    payment_id: str | None,
    order_id: str | None,
    op: Operacao | None,
    db: Session | None = None,
) -> None:
    del gateway
    if not order_id or not op or not mp_configured_for_operacao(op):
        return
    try:
        MercadoPagoClient(access_token=_access_token(db, op)).cancel_order(order_id)
    except MercadoPagoApiError:
        pass
    del payment_id
