from __future__ import annotations

from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from motopay.domain.enums import CobrancaStatus, PaymentMethodType
from motopay.domain.exceptions import ForbiddenError, NotFoundError
from motopay.infrastructure.db.models import Cliente, ClienteMpCard, Cobranca, Contrato, Operacao
from motopay.infrastructure.payments.mercadopago_client import (
    MercadoPagoApiError,
    MercadoPagoClient,
    assert_payer_email_ready,
    mercadopago_api_error_message,
    mp_configured_for_operacao,
    mp_credentials_complete,
    parse_mp_card,
    payer_email_for_mercadopago,
)
from motopay.infrastructure.payments.payment_method_utils import (
    mp_payment_method_type,
    resolve_payment_method_type,
)
from motopay.interfaces.api.deps import CurrentUser
from motopay.interfaces.api.schemas import CardPaymentOut, ClienteMpCardOut, ThreeDsInfoOut
from motopay.services.billing_service import (
    _OPEN_COBRANCA_STATUSES,
    _cobranca_to_out,
    _effective_operacao,
    _finalize_payment,
    charge_amounts_for_cobranca,
)
from motopay.services.mercadopago_token_service import ensure_valid_mp_token


def list_cliente_mp_cards(db: Session, cliente_id: int, operacao_id: int) -> list[ClienteMpCardOut]:
    rows = db.scalars(
        select(ClienteMpCard)
        .where(ClienteMpCard.cliente_id == cliente_id, ClienteMpCard.operacao_id == operacao_id)
        .order_by(ClienteMpCard.is_default.desc(), ClienteMpCard.id.desc())
    ).all()
    return [ClienteMpCardOut.model_validate(r) for r in rows]


def save_cliente_mp_card(
    db: Session,
    user: CurrentUser,
    operacao_scope: int | None,
    *,
    cliente_id: int,
    token: str,
) -> ClienteMpCardOut:
    operacao_id = _effective_operacao(user, operacao_scope)
    cliente = db.get(Cliente, cliente_id)
    if not cliente or cliente.operacao_id != operacao_id:
        raise NotFoundError("Cliente não encontrado")
    op = db.get(Operacao, operacao_id)
    if not op or not mp_credentials_complete(op):
        raise ForbiddenError("Mercado Pago não configurado para esta operação")
    email = payer_email_for_mercadopago(cliente)
    client = MercadoPagoClient(access_token=ensure_valid_mp_token(db, op))
    customer_id = cliente.mercadopago_customer_id
    if not customer_id:
        customer_id = client.get_or_create_customer(
            email=email, first_name=cliente.nome.split()[0], cpf=cliente.cpf
        )
        cliente.mercadopago_customer_id = customer_id
        db.add(cliente)
    card_data = client.save_card(customer_id=customer_id, token=token)
    parsed = parse_mp_card(card_data)
    has_cards = bool(
        list_cliente_mp_cards(db, cliente.id, operacao_id)
    )
    row = ClienteMpCard(
        cliente_id=cliente.id,
        operacao_id=operacao_id,
        mp_card_id=parsed["mp_card_id"],
        payment_method_id=parsed["payment_method_id"],
        last_four_digits=parsed["last_four_digits"],
        cardholder_name=parsed.get("cardholder_name"),
        expiration_month=parsed.get("expiration_month"),
        expiration_year=parsed.get("expiration_year"),
        is_default=not has_cards,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return ClienteMpCardOut.model_validate(row)


def set_default_cliente_mp_card(
    db: Session,
    user: CurrentUser,
    operacao_scope: int | None,
    *,
    cliente_id: int,
    card_id: int,
) -> ClienteMpCardOut:
    operacao_id = _effective_operacao(user, operacao_scope)
    row = db.get(ClienteMpCard, card_id)
    if not row or row.cliente_id != cliente_id or row.operacao_id != operacao_id:
        raise NotFoundError("Cartão não encontrado")
    for other in db.scalars(
        select(ClienteMpCard).where(
            ClienteMpCard.cliente_id == cliente_id,
            ClienteMpCard.operacao_id == operacao_id,
        )
    ).all():
        other.is_default = other.id == card_id
        db.add(other)
    db.commit()
    db.refresh(row)
    return ClienteMpCardOut.model_validate(row)


def delete_cliente_mp_card(
    db: Session,
    user: CurrentUser,
    operacao_scope: int | None,
    *,
    cliente_id: int,
    card_id: int,
) -> None:
    operacao_id = _effective_operacao(user, operacao_scope)
    row = db.get(ClienteMpCard, card_id)
    if not row or row.cliente_id != cliente_id or row.operacao_id != operacao_id:
        raise NotFoundError("Cartão não encontrado")
    op = db.get(Operacao, operacao_id)
    cliente = db.get(Cliente, cliente_id)
    if op and cliente and cliente.mercadopago_customer_id and mp_configured_for_operacao(op):
        try:
            MercadoPagoClient(access_token=ensure_valid_mp_token(db, op)).delete_card(
                customer_id=cliente.mercadopago_customer_id,
                card_id=row.mp_card_id,
            )
        except MercadoPagoApiError:
            pass
    db.delete(row)
    db.commit()


def pay_cobranca_with_card(
    db: Session,
    user: CurrentUser,
    operacao_scope: int | None,
    *,
    cobranca_id: int,
    token: str,
    payment_method_id: str,
    payment_method_kind: Literal["credit_card", "debit_card"] = "credit_card",
    saved_card_id: int | None = None,
    installments: int = 1,
) -> CardPaymentOut:
    from datetime import date

    operacao_id = _effective_operacao(user, operacao_scope)
    cob = db.get(Cobranca, cobranca_id)
    if not cob or cob.operacao_id != operacao_id:
        raise NotFoundError("Cobrança não encontrada")
    if cob.status not in _OPEN_COBRANCA_STATUSES:
        raise ForbiddenError("Cobrança não está aberta para pagamento")
    ct = db.get(Contrato, cob.contrato_id)
    cliente = db.get(Cliente, ct.cliente_id) if ct else None
    op = db.get(Operacao, operacao_id)
    if not ct or not cliente or not op:
        raise NotFoundError("Dados do contrato não encontrados")
    if not mp_credentials_complete(op):
        raise ForbiddenError("Mercado Pago não configurado")
    assert_payer_email_ready(cliente)

    method_type = (
        PaymentMethodType.DEBIT_CARD.value
        if payment_method_kind == "debit_card"
        else PaymentMethodType.CREDIT_CARD.value
    )
    mp_type = mp_payment_method_type(payment_method_kind)
    inst = installments if method_type == PaymentMethodType.CREDIT_CARD.value else 1

    customer_id: str | None = None
    if saved_card_id is not None:
        saved = db.get(ClienteMpCard, saved_card_id)
        if not saved or saved.cliente_id != cliente.id:
            raise NotFoundError("Cartão salvo não encontrado")
        if not token.strip():
            raise ForbiddenError("Informe o CVV (token) para pagar com cartão salvo")
        payment_method_id = saved.payment_method_id
        method_type = resolve_payment_method_type(saved.payment_method_id, method_type)
        customer_id = cliente.mercadopago_customer_id

    today = date.today()
    amounts = charge_amounts_for_cobranca(cob, ct, op, today)
    charge_value = amounts.valor_total
    if cob.valor != charge_value:
        cob.valor = charge_value
        if amounts.dias_atraso > 0:
            cob.status = CobrancaStatus.ATRASADO.value

    client = MercadoPagoClient(access_token=ensure_valid_mp_token(db, op))
    try:
        order = client.create_online_order(
            external_reference=f"cobranca-{cob.id}",
            value=charge_value,
            payer_email=payer_email_for_mercadopago(cliente),
            payer_cpf=cliente.cpf,
            payment_method_id=payment_method_id,
            payment_method_type=mp_type,
            token=token,
            installments=inst,
            customer_id=customer_id,
        )
    except MercadoPagoApiError as exc:
        raise ForbiddenError(
            f"Falha ao processar cartão: {mercadopago_api_error_message(exc)}"
        ) from exc

    cob.mercadopago_order_id = order.order_id
    cob.mercadopago_payment_id = order.payment_id
    cob.payment_gateway = "mercadopago"
    cob.payment_method_type = method_type
    db.add(cob)
    db.flush()

    ev_id: int | None = None
    if order.is_paid:
        # Finalize immediately: creates Financeiro, advances proximo_vencimento,
        # recalculates score and emits domain event. _finalize_payment calls commit.
        _, ev_id = _finalize_payment(
            db,
            cob,
            external_id=order.payment_id,
            gateway="mercadopago",
            value=charge_value,
        )
    else:
        db.commit()

    if ev_id:
        from motopay.infrastructure.messaging.tasks import handle_domain_event
        handle_domain_event.delay(ev_id)

    db.refresh(cob)

    three_ds = None
    if order.three_ds_info:
        three_ds = ThreeDsInfoOut(
            external_resource_url=order.three_ds_info.external_resource_url,
            creq=order.three_ds_info.creq,
        )
    return CardPaymentOut(
        cobranca=_cobranca_to_out(cob, op, date.today(), valor_base=cob.valor),
        order_id=order.order_id,
        payment_id=order.payment_id,
        status=order.order_status,
        requires_3ds=order.requires_3ds,
        three_ds_info=three_ds,
    )
