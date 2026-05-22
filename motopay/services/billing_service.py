from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from sqlalchemy import select
from sqlalchemy.orm import Session

from motopay.config import get_settings
from motopay.domain.enums import (
    CicloCobranca,
    CobrancaStatus,
    ContratoStatus,
    DomainEventType,
    FinanceiroTipo,
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
from motopay.infrastructure.payments.asaas_client import AsaasClient, AsaasPaymentResult
from motopay.interfaces.api.deps import CurrentUser
from motopay.interfaces.api.schemas import CobrancaOut
from motopay.services.late_fee import LateAmounts, calculate_late_amounts
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
    if user.role == UserRole.DONO:
        if user.operacao_id is None:
            raise ForbiddenError("Operação não definida")
        return user.operacao_id
    if operacao_scope is None:
        raise ForbiddenError("Informe operacao_id")
    return operacao_scope


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


def _create_asaas_pix(
    *,
    customer_id: str,
    contrato_id: int,
    valor_total: Decimal,
    due_date: date,
) -> AsaasPaymentResult:
    if _asaas_configured():
        return AsaasClient().create_pix_payment(
            customer_id=customer_id,
            value=valor_total,
            due_date=due_date.isoformat(),
            description=f"Contrato #{contrato_id} — locação moto (atraso)",
        )
    return _synthetic_pix(contrato_id=contrato_id, valor_total=valor_total)


def _cancel_asaas_payment(payment_id: str | None) -> None:
    if not payment_id or not _asaas_configured():
        return
    try:
        AsaasClient().cancel_payment(payment_id)
    except Exception as e:
        logger.warning("asaas_cancel_payment_failed payment_id=%s: %s", payment_id, e)


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
    """DTO com multa/juros calculados a partir do valor base do contrato."""
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


def refresh_overdue_pix(db: Session, *, contrato: Contrato, today: date) -> Cobranca | None:
    """
    Cancela Pix anterior na Asaas (se houver), gera novo com multa/juros do dia
    e atualiza a cobrança aberta do contrato.
    """
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
        and cob.asaas_payment_id
        and cob.pix_copia_cola
    ):
        return cob

    cust_id = ensure_asaas_customer(db, cliente)

    if cob is None:
        pay = _create_asaas_pix(
            customer_id=cust_id,
            contrato_id=contrato.id,
            valor_total=amounts.valor_total,
            due_date=today,
        )
        cob = Cobranca(
            operacao_id=contrato.operacao_id,
            contrato_id=contrato.id,
            valor=amounts.valor_total,
            vencimento=contrato.proximo_vencimento,
            asaas_payment_id=pay.payment_id,
            pix_copia_cola=pay.pix_copia_cola,
            status=CobrancaStatus.ATRASADO.value,
        )
        db.add(cob)
        db.flush()
        return cob

    _cancel_asaas_payment(cob.asaas_payment_id)
    pay = _create_asaas_pix(
        customer_id=cust_id,
        contrato_id=contrato.id,
        valor_total=amounts.valor_total,
        due_date=today,
    )
    cob.valor = amounts.valor_total
    cob.asaas_payment_id = pay.payment_id
    cob.pix_copia_cola = pay.pix_copia_cola
    cob.status = CobrancaStatus.ATRASADO.value
    db.add(cob)
    db.flush()
    return cob


def ensure_asaas_customer(db: Session, cliente: Cliente) -> str:
    if cliente.asaas_customer_id:
        return cliente.asaas_customer_id
    if _asaas_configured():
        client = AsaasClient()
        cid = client.create_customer(name=cliente.nome, cpf_cnpj=cliente.cpf, phone=cliente.telefone)
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
    cust_id = ensure_asaas_customer(db, cliente)
    pay = _create_asaas_pix(
        customer_id=cust_id,
        contrato_id=ct.id,
        valor_total=ct.valor_recorrente,
        due_date=ct.proximo_vencimento,
    )
    cob = Cobranca(
        operacao_id=operacao_id,
        contrato_id=ct.id,
        valor=ct.valor_recorrente,
        vencimento=ct.proximo_vencimento,
        asaas_payment_id=pay.payment_id,
        pix_copia_cola=pay.pix_copia_cola,
        status=CobrancaStatus.PENDENTE.value,
    )
    db.add(cob)
    db.commit()
    db.refresh(cob)
    op = db.get(Operacao, cob.operacao_id)
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


def list_cobrancas(db: Session, user: CurrentUser, operacao_scope: int | None) -> list[CobrancaOut]:
    q = select(Cobranca)
    if user.role == UserRole.DONO:
        q = q.where(Cobranca.operacao_id == user.operacao_id)
    elif operacao_scope is not None:
        q = q.where(Cobranca.operacao_id == operacao_scope)
    rows = list(db.scalars(q.order_by(Cobranca.id.desc())).all())
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
    return out


def handle_payment_confirmed(
    db: Session,
    *,
    asaas_payment_id: str,
    value: Decimal | None = None,
) -> tuple[bool, int | None]:
    """Idempotente. Retorna (processado_ou_idempotente, evento_id_para_fila)."""
    cob = db.scalars(select(Cobranca).where(Cobranca.asaas_payment_id == asaas_payment_id)).first()
    if not cob:
        return False, None
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
        descricao=f"Pagamento confirmado (Asaas {asaas_payment_id})",
        data=date.today(),
        moto_id=ct.moto_id,
        contrato_id=ct.id,
    )
    db.add(fin)

    ct.proximo_vencimento = add_cycle(ct.proximo_vencimento, ct.ciclo)
    ct.inadimplente = False
    ct.nivel_escalonamento_cobranca = 0
    ct.dias_atraso_acumulado = 0
    db.add(ct)

    cliente = db.get(Cliente, ct.cliente_id)
    if cliente:
        recalculate_cliente_score(db, cliente, on_time_payment_delta=5)

    ev = EventoDominio(
        tipo=DomainEventType.PAGAMENTO_CONFIRMADO.value,
        payload={
            "contrato_id": ct.id,
            "cliente_id": ct.cliente_id,
            "asaas_payment_id": asaas_payment_id,
            "operacao_id": cob.operacao_id,
        },
    )
    db.add(ev)
    db.flush()
    ev_id = ev.id
    db.commit()
    return True, ev_id
