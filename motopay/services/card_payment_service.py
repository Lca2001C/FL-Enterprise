from __future__ import annotations



from datetime import date

from decimal import Decimal

from typing import Literal



from sqlalchemy import select

from sqlalchemy.orm import Session



from motopay.domain.enums import CobrancaStatus, PaymentMethodType

from motopay.infrastructure.payments.payment_method_utils import (

    installments_for_payment_method,

    is_debit_payment_method_id,

    resolve_payment_method_type,

)

from motopay.domain.exceptions import ForbiddenError, NotFoundError

from motopay.infrastructure.db.models import Cliente, ClienteMpCard, Cobranca, Contrato, Operacao

from motopay.infrastructure.payments.mercadopago_client import (
    MercadoPagoClient,
    _parse_mp_card,
    mercadopago_api_error_message,
    mp_configured_for_operacao,
    mp_credentials_complete,
    mp_token_for_operacao,
    payer_email_for_mercadopago,
    uses_operacao_mercadopago_credentials,
)

from motopay.infrastructure.payments.mercadopago_sdk import MercadoPagoApiError

from motopay.interfaces.api.deps import CurrentUser

from motopay.interfaces.api.schemas import CardPaymentOut, ClienteMpCardOut, ThreeDsInfoOut

from motopay.services.billing_service import (

    _OPEN_COBRANCA_STATUSES,

    _effective_operacao,

    handle_mercadopago_order_confirmed,

)

from motopay.services.late_fee import calculate_late_amounts





def _mp_client_for_operacao(op: Operacao) -> MercadoPagoClient:

    if not mp_configured_for_operacao(op):

        raise ForbiddenError("Mercado Pago não configurado para esta operação")

    if uses_operacao_mercadopago_credentials(op) and not mp_credentials_complete(op):

        raise ForbiddenError(

            "Credenciais Mercado Pago incompletas. Configure Access Token, Public Key e "

            "Webhook Secret em Ajustes."

        )

    return MercadoPagoClient(access_token=mp_token_for_operacao(op))





def _get_cliente_scoped(

    db: Session, user: CurrentUser, operacao_scope: int | None, cliente_id: int

) -> Cliente:

    operacao_id = _effective_operacao(user, operacao_scope)

    cliente = db.get(Cliente, cliente_id)

    if not cliente or cliente.operacao_id != operacao_id:

        raise NotFoundError("Cliente não encontrado")

    return cliente





def _card_to_out(card: ClienteMpCard) -> ClienteMpCardOut:

    return ClienteMpCardOut(

        id=card.id,

        mp_card_id=card.mp_card_id,

        payment_method_id=card.payment_method_id,

        last_four_digits=card.last_four_digits,

        cardholder_name=card.cardholder_name,

        expiration_month=card.expiration_month,

        expiration_year=card.expiration_year,

        is_default=card.is_default,

    )





def _ensure_mp_customer(db: Session, cliente: Cliente, mp: MercadoPagoClient) -> str:

    if cliente.mercadopago_customer_id:

        return cliente.mercadopago_customer_id

    parts = cliente.nome.strip().split(maxsplit=1)

    first = parts[0] if parts else "Cliente"

    last = parts[1] if len(parts) > 1 else ""

    email = payer_email_for_mercadopago(cliente.id)

    customer_id = mp.ensure_customer(

        email=email,

        cpf=cliente.cpf,

        first_name=first,

        last_name=last,

        external_reference=f"cliente-{cliente.id}",

    )

    cliente.mercadopago_customer_id = customer_id

    db.add(cliente)

    db.flush()

    return customer_id





def list_cliente_cards(

    db: Session,

    user: CurrentUser,

    operacao_scope: int | None,

    cliente_id: int,

) -> list[ClienteMpCardOut]:

    cliente = _get_cliente_scoped(db, user, operacao_scope, cliente_id)

    rows = list(

        db.scalars(

            select(ClienteMpCard)

            .where(ClienteMpCard.cliente_id == cliente.id)

            .order_by(ClienteMpCard.is_default.desc(), ClienteMpCard.id.desc())

        ).all()

    )

    return [_card_to_out(c) for c in rows]





def save_cliente_card(

    db: Session,

    user: CurrentUser,

    operacao_scope: int | None,

    cliente_id: int,

    *,

    card_token: str,

) -> ClienteMpCardOut:

    cliente = _get_cliente_scoped(db, user, operacao_scope, cliente_id)

    op = db.get(Operacao, cliente.operacao_id)

    if not op:

        raise NotFoundError("Operação não encontrada")

    mp = _mp_client_for_operacao(op)

    customer_id = _ensure_mp_customer(db, cliente, mp)

    raw = mp.save_card(customer_id, card_token.strip())

    parsed = _parse_mp_card(raw)



    existing = db.scalars(

        select(ClienteMpCard).where(

            ClienteMpCard.cliente_id == cliente.id,

            ClienteMpCard.mp_card_id == parsed["mp_card_id"],

        )

    ).first()

    if existing:

        return _card_to_out(existing)



    is_first = (

        db.scalar(

            select(ClienteMpCard.id).where(ClienteMpCard.cliente_id == cliente.id).limit(1)

        )

        is None

    )

    card = ClienteMpCard(

        cliente_id=cliente.id,

        operacao_id=cliente.operacao_id,

        mp_card_id=parsed["mp_card_id"],

        payment_method_id=parsed["payment_method_id"],

        last_four_digits=parsed["last_four_digits"],

        cardholder_name=parsed.get("cardholder_name"),

        expiration_month=parsed.get("expiration_month"),

        expiration_year=parsed.get("expiration_year"),

        is_default=is_first,

    )

    db.add(card)

    db.commit()

    db.refresh(card)

    return _card_to_out(card)





def delete_cliente_card(

    db: Session,

    user: CurrentUser,

    operacao_scope: int | None,

    cliente_id: int,

    card_row_id: int,

) -> None:

    cliente = _get_cliente_scoped(db, user, operacao_scope, cliente_id)

    card = db.get(ClienteMpCard, card_row_id)

    if not card or card.cliente_id != cliente.id:

        raise NotFoundError("Cartão não encontrado")

    op = db.get(Operacao, cliente.operacao_id)

    if not op:

        raise NotFoundError("Operação não encontrada")

    mp = _mp_client_for_operacao(op)

    if cliente.mercadopago_customer_id:

        try:

            mp.delete_card(cliente.mercadopago_customer_id, card.mp_card_id)

        except MercadoPagoApiError:

            pass

    db.delete(card)

    db.commit()





def _payment_kind_from_method(

    pm_id: str,

    payment_method_kind: str | None,

) -> Literal["credit_card", "debit_card"]:

    if payment_method_kind == PaymentMethodType.DEBIT_CARD.value:

        return "debit_card"

    if payment_method_kind == PaymentMethodType.CREDIT_CARD.value:

        return "credit_card"

    return "debit_card" if is_debit_payment_method_id(pm_id) else "credit_card"





def pay_cobranca_with_card(

    db: Session,

    user: CurrentUser,

    operacao_scope: int | None,

    cobranca_id: int,

    *,

    token: str | None = None,

    saved_card_id: int | None = None,

    installments: int = 1,

    payment_method_id: str | None = None,

    payment_method_kind: str | None = None,

) -> CardPaymentOut:

    operacao_id = _effective_operacao(user, operacao_scope)

    cob = db.get(Cobranca, cobranca_id)

    if not cob or cob.operacao_id != operacao_id:

        raise NotFoundError("Cobrança não encontrada")

    if cob.status not in _OPEN_COBRANCA_STATUSES:

        raise ForbiddenError("Cobrança não está aberta para pagamento")



    ct = db.get(Contrato, cob.contrato_id)

    if not ct:

        raise NotFoundError("Contrato não encontrado")

    cliente = db.get(Cliente, ct.cliente_id)

    if not cliente:

        raise NotFoundError("Cliente não encontrado")

    op = db.get(Operacao, operacao_id)

    if not op:

        raise NotFoundError("Operação não encontrada")



    if not token or not token.strip():

        raise ForbiddenError(

            "Token do cartão é obrigatório. Use o formulário abaixo para informar o CVV."

        )



    mp = _mp_client_for_operacao(op)

    amounts = calculate_late_amounts(

        valor_base=cob.valor,

        vencimento=cob.vencimento,

        operacao=op,

        today=date.today(),

    )

    pm_id = (payment_method_id or "visa").strip()

    customer_id: str | None = None



    if saved_card_id is not None:

        card_row = db.get(ClienteMpCard, saved_card_id)

        if not card_row or card_row.cliente_id != cliente.id:

            raise NotFoundError("Cartão salvo não encontrado")

        if payment_method_kind == PaymentMethodType.CREDIT_CARD.value and is_debit_payment_method_id(

            card_row.payment_method_id

        ):

            raise ForbiddenError("Este cartão salvo é de débito; use a aba Cartão de débito.")

        if payment_method_kind == PaymentMethodType.DEBIT_CARD.value and not is_debit_payment_method_id(

            card_row.payment_method_id

        ):

            raise ForbiddenError("Este cartão salvo é de crédito; use a aba Cartão de crédito.")

        customer_id = _ensure_mp_customer(db, cliente, mp)

        pm_id = card_row.payment_method_id



    method_type = resolve_payment_method_type(pm_id, explicit_kind=payment_method_kind)

    inst = installments_for_payment_method(

        pm_id, installments, explicit_kind=payment_method_kind

    )

    card_kind = _payment_kind_from_method(pm_id, payment_method_kind)



    try:

        result = mp.create_online_order(

            external_reference=f"cobranca-{cob.id}",

            value=amounts.valor_total,

            payer_email=payer_email_for_mercadopago(cliente.id),

            payer_cpf=cliente.cpf,

            customer_id=customer_id,

            payment_kind=card_kind,

            payment_method_id=pm_id,

            token=token.strip(),

            installments=inst,

            idempotency_key=f"card-cobranca-{cob.id}",

        )

    except MercadoPagoApiError as exc:

        raise ForbiddenError(
            f"Falha ao processar cartão: {mercadopago_api_error_message(exc)}"
        ) from exc



    cob.mercadopago_order_id = result.order_id

    cob.mercadopago_payment_id = result.payment_id

    cob.valor = amounts.valor_total

    cob.pix_copia_cola = None

    cob.payment_method_type = method_type

    db.add(cob)



    event_id: int | None = None

    if result.is_paid:

        _, event_id = handle_mercadopago_order_confirmed(

            db,

            mercadopago_order_id=result.order_id,

            value=amounts.valor_total,

        )

    else:

        db.commit()



    three_ds_out = None

    if result.three_ds_info:

        three_ds_out = ThreeDsInfoOut(

            external_resource_url=result.three_ds_info.external_resource_url,

            creq=result.three_ds_info.creq,

        )



    return CardPaymentOut(

        payment_id=result.payment_id,

        status=result.payment_status or result.order_status,

        status_detail=result.status_detail,

        requires_3ds=result.requires_3ds,

        three_ds_info=three_ds_out,

        cobranca_finalizada=result.is_paid,

        domain_event_id=event_id,

        payment_method_type=method_type,

    )


