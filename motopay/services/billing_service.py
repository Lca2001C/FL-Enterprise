from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from motopay.config import get_settings
from motopay.domain.enums import (
    CicloCobranca,
    CobrancaStatus,
    ContratoStatus,
    DomainEventType,
    FinanceiroTipo,
    PaymentGateway,
    PaymentProvider,
    UserRole,
)
from motopay.domain.exceptions import ForbiddenError, NotFoundError
from motopay.infrastructure.db.models import (
    Cliente,
    Cobranca,
    Contrato,
    EventoDominio,
    Financeiro,
    Operacao,
)
from motopay.infrastructure.payments.asaas_client import AsaasClient
from motopay.infrastructure.payments.mercadopago_client import (
    MercadoPagoClient,
    mp_configured_for_operacao,
    mp_token_for_operacao,
)
from motopay.interfaces.api.deps import CurrentUser
from motopay.interfaces.api.schemas import CobrancaOut
from motopay.services.late_fee import LateAmounts, calculate_late_amounts
from motopay.services.payment_gateway import cancel_external_payment, create_pix_for_contrato
from motopay.services.scoring_service import recalculate_cliente_score

logger = logging.getLogger(__name__)

_OPEN_COBRANCA_STATUSES = (
    CobrancaStatus.PENDENTE.value,
    CobrancaStatus.ATRASADO.value,
)


def add_cycle(d: date, ciclo: str) -> date:
    if ciclo == CicloCobranca.SEMANAL.value:
        return d + timedelta(days=7)
    return d + relativedelta(months=1)


def _effective_operacao(user: CurrentUser, operacao_scope: int | None) -> int:
    if user.role in (UserRole.DONO, UserRole.OPERADOR):
        if user.operacao_id is None:
            raise ForbiddenError("Operação não definida")
        return user.operacao_id
    if operacao_scope is None:
        raise ForbiddenError("Informe operacao_id")
    return operacao_scope


def _asaas_configured() -> bool:
    return bool(get_settings().asaas_api_key.strip())


def _cobranca_query(user: CurrentUser, operacao_scope: int | None):
    q = select(Cobranca)
    if user.role in (UserRole.DONO, UserRole.OPERADOR):
        q = q.where(Cobranca.operacao_id == user.operacao_id)
    elif operacao_scope is not None:
        q = q.where(Cobranca.operacao_id == operacao_scope)
    return q


def get_open_cobranca(db: Session, contrato_id: int) -> Cobranca | None:
    return db.scalars(
        select(Cobranca)
        .where(
            Cobranca.contrato_id == contrato_id,
            Cobranca.status.in_(_OPEN_COBRANCA_STATUSES),
        )
        .order_by(Cobranca.id.desc())
    ).first()


def _cobranca_to_out(
    c: Cobranca,
    op: Operacao | None,
    today: date,
    *,
    valor_base: Decimal | None = None,
) -> CobrancaOut:
    base = valor_base if valor_base is not None else c.valor
    display_status = c.status
    pendente_ou_atrasado = c.status in _OPEN_COBRANCA_STATUSES
    if pendente_ou_atrasado and c.vencimento < today:
        amounts = calculate_late_amounts(
            valor_base=base,
            vencimento=c.vencimento,
            operacao=op,
            today=today,
        )
        display_status = CobrancaStatus.ATRASADO.value
    else:
        amounts = calculate_late_amounts(
            valor_base=base,
            vencimento=c.vencimento,
            operacao=op,
            today=today,
        )

    return CobrancaOut(
        id=c.id,
        operacao_id=c.operacao_id,
        contrato_id=c.contrato_id,
        valor=base,
        vencimento=c.vencimento,
        asaas_payment_id=c.asaas_payment_id,
        mercadopago_payment_id=c.mercadopago_payment_id,
        payment_gateway=c.payment_gateway or PaymentGateway.ASAAS.value,
        pix_copia_cola=c.pix_copia_cola,
        status=display_status,
        dias_atraso=amounts.dias_atraso,
        multa=amounts.multa,
        juros=amounts.juros,
        valor_total=amounts.valor_total,
    )


def late_amounts_for_contrato(
    db: Session,
    contrato: Contrato,
    today: date,
) -> LateAmounts:
    op = db.get(Operacao, contrato.operacao_id)
    return calculate_late_amounts(
        valor_base=contrato.valor_recorrente,
        vencimento=contrato.proximo_vencimento,
        operacao=op,
        today=today,
    )


def _apply_pix_to_cobranca(
    cob: Cobranca,
    *,
    external_id: str,
    pix: str | None,
    gateway: str,
    valor: Decimal,
    status: str,
) -> None:
    cob.valor = valor
    cob.pix_copia_cola = pix
    cob.payment_gateway = gateway
    cob.status = status
    if gateway == PaymentGateway.MERCADOPAGO.value:
        cob.mercadopago_payment_id = external_id
        cob.asaas_payment_id = None
    else:
        cob.asaas_payment_id = external_id
        cob.mercadopago_payment_id = None


def refresh_overdue_pix(db: Session, *, contrato: Contrato, today: date) -> Cobranca | None:
    if contrato.status != ContratoStatus.ATIVO.value:
        return None
    if contrato.proximo_vencimento >= today:
        return None

    op = db.get(Operacao, contrato.operacao_id)
    if not op:
        return None

    amounts = calculate_late_amounts(
        valor_base=contrato.valor_recorrente,
        vencimento=contrato.proximo_vencimento,
        operacao=op,
        today=today,
    )
    if amounts.dias_atraso <= 0:
        return None

    cliente = db.get(Cliente, contrato.cliente_id)
    if not cliente:
        return None

    cob = get_open_cobranca(db, contrato.id)
    if (
        cob is not None
        and cob.status == CobrancaStatus.ATRASADO.value
        and cob.valor == amounts.valor_total
        and (cob.asaas_payment_id or cob.mercadopago_payment_id)
        and cob.pix_copia_cola
    ):
        return cob

    cust_id = ensure_asaas_customer(db, cliente)
    gateway = cob.payment_gateway if cob else PaymentGateway.ASAAS.value
    if cob is not None:
        cancel_external_payment(
            gateway=gateway, payment_id=cob.asaas_payment_id or cob.mercadopago_payment_id, op=op
        )

    ext_id, pix, gw = create_pix_for_contrato(
        op=op,
        cliente=cliente,
        contrato_id=contrato.id,
        valor_total=amounts.valor_total,
        due_date=today,
        asaas_customer_id=cust_id,
    )

    if cob is None:
        cob = Cobranca(
            operacao_id=contrato.operacao_id,
            contrato_id=contrato.id,
            valor=amounts.valor_total,
            vencimento=contrato.proximo_vencimento,
            status=CobrancaStatus.ATRASADO.value,
        )
        db.add(cob)
    _apply_pix_to_cobranca(
        cob,
        external_id=ext_id,
        pix=pix,
        gateway=gw,
        valor=amounts.valor_total,
        status=CobrancaStatus.ATRASADO.value,
    )
    db.add(cob)
    db.flush()
    return cob


def ensure_asaas_customer(db: Session, cliente: Cliente) -> str:
    if cliente.asaas_customer_id:
        return cliente.asaas_customer_id
    if _asaas_configured():
        client = AsaasClient()
        cid = client.create_customer(
            name=cliente.nome, cpf_cnpj=cliente.cpf, phone=cliente.telefone
        )
    else:
        cid = f"demo_cust_{cliente.id}"
    cliente.asaas_customer_id = cid
    db.add(cliente)
    db.flush()
    return cid


def create_pix_charge_for_contract(
    db: Session,
    user: CurrentUser,
    operacao_scope: int | None,
    contrato_id: int,
) -> CobrancaOut:
    operacao_id = _effective_operacao(user, operacao_scope)
    ct = db.get(Contrato, contrato_id)
    if not ct or ct.operacao_id != operacao_id:
        raise NotFoundError("Contrato não encontrado")
    cliente = db.get(Cliente, ct.cliente_id)
    if not cliente:
        raise NotFoundError("Cliente não encontrado")
    op = db.get(Operacao, operacao_id)
    if not op:
        raise NotFoundError("Operação não encontrada")
    cust_id = ensure_asaas_customer(db, cliente)
    ext_id, pix, gw = create_pix_for_contrato(
        op=op,
        cliente=cliente,
        contrato_id=ct.id,
        valor_total=ct.valor_recorrente,
        due_date=ct.proximo_vencimento,
        asaas_customer_id=cust_id,
    )
    cob = Cobranca(
        operacao_id=operacao_id,
        contrato_id=ct.id,
        valor=ct.valor_recorrente,
        vencimento=ct.proximo_vencimento,
        pix_copia_cola=pix,
        payment_gateway=gw,
        status=CobrancaStatus.PENDENTE.value,
    )
    _apply_pix_to_cobranca(
        cob,
        external_id=ext_id,
        pix=pix,
        gateway=gw,
        valor=ct.valor_recorrente,
        status=CobrancaStatus.PENDENTE.value,
    )
    db.add(cob)
    db.commit()
    db.refresh(cob)
    return _cobranca_to_out(cob, op, date.today(), valor_base=ct.valor_recorrente)


def create_asaas_subscription_for_contract(
    db: Session,
    user: CurrentUser,
    operacao_scope: int | None,
    contrato_id: int,
) -> Contrato:
    operacao_id = _effective_operacao(user, operacao_scope)
    ct = db.get(Contrato, contrato_id)
    if not ct or ct.operacao_id != operacao_id:
        raise NotFoundError("Contrato não encontrado")
    cliente = db.get(Cliente, ct.cliente_id)
    if not cliente:
        raise NotFoundError("Cliente não encontrado")
    cust_id = ensure_asaas_customer(db, cliente)
    sub_id = AsaasClient().create_subscription(
        customer_id=cust_id,
        value=ct.valor_recorrente,
        cycle=ct.ciclo,
        description=f"Contrato #{ct.id}",
        next_due=ct.proximo_vencimento.isoformat(),
    )
    ct.asaas_subscription_id = sub_id
    db.add(ct)
    db.commit()
    db.refresh(ct)
    return ct


def create_mercadopago_subscription_for_contract(
    db: Session,
    user: CurrentUser,
    operacao_scope: int | None,
    contrato_id: int,
) -> Contrato:
    operacao_id = _effective_operacao(user, operacao_scope)
    ct = db.get(Contrato, contrato_id)
    if not ct or ct.operacao_id != operacao_id:
        raise NotFoundError("Contrato não encontrado")
    op = db.get(Operacao, operacao_id)
    if not op or op.payment_provider != PaymentProvider.MERCADOPAGO.value:
        raise ForbiddenError("Operação não usa Mercado Pago")
    if not mp_configured_for_operacao(op):
        raise ForbiddenError("Mercado Pago não configurado")
    cliente = db.get(Cliente, ct.cliente_id)
    if not cliente:
        raise NotFoundError("Cliente não encontrado")
    sub_id = MercadoPagoClient(access_token=mp_token_for_operacao(op)).create_preapproval(
        external_reference=f"contrato-{ct.id}",
        value=ct.valor_recorrente,
        reason=f"Contrato #{ct.id}",
        payer_email=f"cliente{cliente.id}@motopay.local",
    )
    ct.mercadopago_subscription_id = sub_id
    db.add(ct)
    db.commit()
    db.refresh(ct)
    return ct


def list_cobrancas(
    db: Session,
    user: CurrentUser,
    operacao_scope: int | None,
    *,
    limit: int,
    offset: int,
    status: CobrancaStatus | None = None,
) -> tuple[list[CobrancaOut], int]:
    base = _cobranca_query(user, operacao_scope)
    if status is not None:
        base = base.where(Cobranca.status == status.value)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = list(db.scalars(base.order_by(Cobranca.id.desc()).limit(limit).offset(offset)).all())
    today = date.today()
    op_ids = {c.operacao_id for c in rows}
    ops: dict[int, Operacao] = {}
    if op_ids:
        for o in db.scalars(select(Operacao).where(Operacao.id.in_(op_ids))).all():
            ops[o.id] = o
    ct_ids = {c.contrato_id for c in rows}
    contratos: dict[int, Contrato] = {}
    if ct_ids:
        for ct in db.scalars(select(Contrato).where(Contrato.id.in_(ct_ids))).all():
            contratos[ct.id] = ct
    out: list[CobrancaOut] = []
    for c in rows:
        ct = contratos.get(c.contrato_id)
        valor_base = ct.valor_recorrente if ct else c.valor
        out.append(_cobranca_to_out(c, ops.get(c.operacao_id), today, valor_base=valor_base))
    return out, int(total)


def list_cobrancas_for_cliente(
    db: Session,
    *,
    cliente_id: int,
    limit: int,
    offset: int,
) -> tuple[list[CobrancaOut], int]:
    q = (
        select(Cobranca)
        .join(Contrato, Contrato.id == Cobranca.contrato_id)
        .where(Contrato.cliente_id == cliente_id)
    )
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = list(db.scalars(q.order_by(Cobranca.id.desc()).limit(limit).offset(offset)).all())
    today = date.today()
    out: list[CobrancaOut] = []
    for c in rows:
        ct = db.get(Contrato, c.contrato_id)
        op = db.get(Operacao, c.operacao_id)
        valor_base = ct.valor_recorrente if ct else c.valor
        out.append(_cobranca_to_out(c, op, today, valor_base=valor_base))
    return out, int(total)


def get_active_contrato_for_cliente(db: Session, cliente_id: int) -> Contrato | None:
    return db.scalars(
        select(Contrato)
        .where(
            Contrato.cliente_id == cliente_id,
            Contrato.status == ContratoStatus.ATIVO.value,
        )
        .order_by(Contrato.id.desc())
    ).first()


def _finalize_payment(
    db: Session,
    cob: Cobranca,
    *,
    external_id: str,
    gateway: str,
    value: Decimal | None,
) -> tuple[bool, int | None]:
    if cob.status == CobrancaStatus.RECEBIDO.value:
        return True, None

    cob.status = CobrancaStatus.RECEBIDO.value
    db.add(cob)

    ct = db.get(Contrato, cob.contrato_id)
    if not ct:
        db.commit()
        return True, None

    amount = value if value is not None else cob.valor
    fin = Financeiro(
        operacao_id=cob.operacao_id,
        tipo=FinanceiroTipo.RECEITA.value,
        valor=amount,
        descricao=f"Pagamento confirmado ({gateway} {external_id})",
        data=date.today(),
        moto_id=ct.moto_id,
        contrato_id=ct.id,
    )
    db.add(fin)

    ct.proximo_vencimento = add_cycle(ct.proximo_vencimento, ct.ciclo)
    ct.inadimplente = False
    ct.nivel_escalonamento_cobranca = 0
    ct.dias_atraso_acumulado = 0
    ct.promessa_pagamento_em = None
    ct.promessa_notas = None
    db.add(ct)

    cliente = db.get(Cliente, ct.cliente_id)
    if cliente:
        recalculate_cliente_score(db, cliente, on_time_payment_delta=5)

    payload: dict = {
        "contrato_id": ct.id,
        "cliente_id": ct.cliente_id,
        "operacao_id": cob.operacao_id,
    }
    if gateway == PaymentGateway.MERCADOPAGO.value:
        payload["mercadopago_payment_id"] = external_id
    else:
        payload["asaas_payment_id"] = external_id

    ev = EventoDominio(
        tipo=DomainEventType.PAGAMENTO_CONFIRMADO.value,
        payload=payload,
    )
    db.add(ev)
    db.flush()
    ev_id = ev.id
    db.commit()
    return True, ev_id


def handle_payment_confirmed(
    db: Session,
    *,
    asaas_payment_id: str,
    value: Decimal | None = None,
) -> tuple[bool, int | None]:
    cob = db.scalars(select(Cobranca).where(Cobranca.asaas_payment_id == asaas_payment_id)).first()
    if not cob:
        return False, None
    return _finalize_payment(
        db,
        cob,
        external_id=asaas_payment_id,
        gateway=PaymentGateway.ASAAS.value,
        value=value,
    )


def handle_mercadopago_payment_confirmed(
    db: Session,
    *,
    mercadopago_payment_id: str,
    value: Decimal | None = None,
) -> tuple[bool, int | None]:
    cob = db.scalars(
        select(Cobranca).where(Cobranca.mercadopago_payment_id == mercadopago_payment_id)
    ).first()
    if not cob:
        return False, None
    return _finalize_payment(
        db,
        cob,
        external_id=mercadopago_payment_id,
        gateway=PaymentGateway.MERCADOPAGO.value,
        value=value,
    )
