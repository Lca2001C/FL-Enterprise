from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from motopay.domain.enums import PaymentGateway
from motopay.domain.exceptions import MotoPayError
from motopay.infrastructure.db.models import Cliente, Contrato, Operacao
from motopay.infrastructure.payments.mercadopago_client import (
    MercadoPagoApiError,
    MercadoPagoClient,
    assert_payer_email_ready,
    mp_configured_for_operacao,
    mp_credentials_complete,
    mp_token_for_operacao,
    payer_email_for_mercadopago,
)
from motopay.infrastructure.payments.mp_payload_builder import (
    MercadoPagoDataError,
    build_additional_info,
    build_items_for_contrato,
    build_mp_payer,
    build_statement_descriptor,
)
from motopay.services.mercadopago_token_service import ensure_valid_mp_token


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


def _build_mp_enrichment(
    *,
    op: Operacao,
    cliente: Cliente,
    valor_total: Decimal,
    contrato: Contrato | None,
) -> dict[str, object]:
    """Constrói payer/items/additional_info/statement_descriptor — todos opcionais.

    Em caso de dados incompletos do cliente (sem endereço, etc.), os campos
    opcionais são omitidos mas os obrigatórios (items, payer) seguem.
    """
    payer_email = payer_email_for_mercadopago(cliente)
    payer = build_mp_payer(cliente, fallback_email=payer_email)
    payer.pop("email", None)
    items = build_items_for_contrato(
        contrato,
        moto=getattr(contrato, "moto", None) if contrato else None,
        total_value=valor_total,
    )
    add_info = build_additional_info(cliente)
    return {
        "payer_extra": payer,
        "payer_email": payer_email,
        "items": items,
        "additional_info": add_info,
        "statement_descriptor": build_statement_descriptor(op.nome),
        "description": items[0]["description"] if items and items[0].get("description") else items[0]["title"],
    }


def create_pix_for_cobranca(
    *,
    op: Operacao,
    cliente: Cliente,
    cobranca_id: int,
    valor_total: Decimal,
    due_date: date,
    db: Session | None = None,
    contrato: Contrato | None = None,
    device_id: str | None = None,
) -> tuple[str, str, str | None, str]:
    """Retorna (order_id, payment_id, pix_copia_cola, gateway)."""
    del due_date
    if not mp_credentials_complete(op):
        if mp_configured_for_operacao(op):
            raise MotoPayError(
                "Credenciais Mercado Pago incompletas. Configure Access Token, Public Key e "
                "Webhook Secret em Ajustes."
            )
    if mp_configured_for_operacao(op) and mp_credentials_complete(op):
        assert_payer_email_ready(cliente)
        try:
            extra = _build_mp_enrichment(
                op=op, cliente=cliente, valor_total=valor_total, contrato=contrato
            )
        except MercadoPagoDataError as exc:
            raise MotoPayError(str(exc)) from exc
        order = MercadoPagoClient(access_token=_access_token(db, op)).create_online_order(
            external_reference=f"cobranca-{cobranca_id}",
            value=valor_total,
            payer_email=extra["payer_email"],  # type: ignore[arg-type]
            payer_cpf=cliente.cpf,
            payment_method_id="pix",
            payment_method_type="bank_transfer",
            items=extra["items"],  # type: ignore[arg-type]
            device_id=device_id,
        )
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
    contrato: Contrato | None = None,
    device_id: str | None = None,
) -> tuple[str, str, str | None, str]:
    """Compat: Pix por contrato (usa cobranca-{contrato_id} como referência externa)."""
    del due_date
    if mp_configured_for_operacao(op) and mp_credentials_complete(op):
        assert_payer_email_ready(cliente)
        try:
            extra = _build_mp_enrichment(
                op=op, cliente=cliente, valor_total=valor_total, contrato=contrato
            )
        except MercadoPagoDataError as exc:
            raise MotoPayError(str(exc)) from exc
        order = MercadoPagoClient(access_token=_access_token(db, op)).create_online_order(
            external_reference=f"contrato-{contrato_id}",
            value=valor_total,
            payer_email=extra["payer_email"],  # type: ignore[arg-type]
            payer_cpf=cliente.cpf,
            payment_method_id="pix",
            payment_method_type="bank_transfer",
            items=extra["items"],  # type: ignore[arg-type]
            device_id=device_id,
        )
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
    import logging

    _log = logging.getLogger(__name__)
    del gateway
    if not op or not mp_configured_for_operacao(op):
        return
    if not order_id:
        if payment_id:
            _log.warning(
                "cancel_external_payment: order_id ausente para payment_id=%s — cancelamento ignorado",
                payment_id,
            )
        return
    try:
        MercadoPagoClient(access_token=_access_token(db, op)).cancel_order(order_id)
    except MercadoPagoApiError as exc:
        # 400/404/422 indicam ordem já em estado terminal — seguro ignorar
        if exc.status_code not in (400, 404, 422):
            _log.warning(
                "cancel_order falhou order_id=%s payment_id=%s status=%s",
                order_id, payment_id, exc.status_code,
            )
