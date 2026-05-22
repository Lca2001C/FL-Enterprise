from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from sqlalchemy import select
from sqlalchemy.orm import Session

from motopay.domain.enums import (
    CicloCobranca,
    CobrancaStatus,
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
from motopay.infrastructure.payments.asaas_client import AsaasClient
from motopay.interfaces.api.deps import CurrentUser
from motopay.interfaces.api.schemas import CobrancaOut
from motopay.services.scoring_service import recalculate_cliente_score


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


def _cobranca_to_out(c: Cobranca, op: Operacao | None, today: date) -> CobrancaOut:
    """DTO com multa/juros calculados sem alterar o ORM (evita GET sujo e atributos inexistentes)."""
    m_pct = (op.multa_fixa_percentual / Decimal("100")) if op else Decimal(0)
    j_pct = (op.juros_diario_percentual / Decimal("100")) if op else Decimal(0)
    dias_atraso = 0
    multa = Decimal(0)
    juros = Decimal(0)
    display_status = c.status
    pendente_ou_atrasado = c.status in (
        CobrancaStatus.PENDENTE.value,
        CobrancaStatus.ATRASADO.value,
    )
    if pendente_ou_atrasado and c.vencimento < today:
        dias_atraso = (today - c.vencimento).days
        multa = (c.valor * m_pct).quantize(Decimal("0.01"))
        juros = (c.valor * j_pct * dias_atraso).quantize(Decimal("0.01"))
        display_status = CobrancaStatus.ATRASADO.value
    valor_total = (c.valor + multa + juros).quantize(Decimal("0.01"))
    return CobrancaOut(
        id=c.id,
        operacao_id=c.operacao_id,
        contrato_id=c.contrato_id,
        valor=c.valor,
        vencimento=c.vencimento,
        asaas_payment_id=c.asaas_payment_id,
        pix_copia_cola=c.pix_copia_cola,
        status=display_status,
        dias_atraso=dias_atraso,
        multa=multa,
        juros=juros,
        valor_total=valor_total,
    )


def ensure_asaas_customer(db: Session, cliente: Cliente) -> str:
    if cliente.asaas_customer_id:
        return cliente.asaas_customer_id
    client = AsaasClient()
    cid = client.create_customer(name=cliente.nome, cpf_cnpj=cliente.cpf, phone=cliente.telefone)
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
    due = ct.proximo_vencimento.isoformat()
    pay = AsaasClient().create_pix_payment(
        customer_id=cust_id,
        value=ct.valor_recorrente,
        due_date=due,
        description=f"Contrato #{ct.id} — locação moto",
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
    return _cobranca_to_out(cob, op, date.today())


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
    return [_cobranca_to_out(c, ops.get(c.operacao_id), today) for c in rows]


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
