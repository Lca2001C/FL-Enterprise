from __future__ import annotations

from datetime import date, timedelta

from decimal import Decimal

from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session

from motopay.domain.enums import CicloCobranca, CobrancaStatus, DomainEventType, FinanceiroTipo, UserRole
from motopay.domain.exceptions import ForbiddenError, NotFoundError
from motopay.infrastructure.db.models import Cliente, Cobranca, Contrato, EventoDominio, Financeiro
from motopay.infrastructure.payments.asaas_client import AsaasClient
from motopay.interfaces.api.deps import CurrentUser
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
) -> Cobranca:
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
    return cob


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


def list_cobrancas(db: Session, user: CurrentUser, operacao_scope: int | None) -> list[Cobranca]:
    from sqlalchemy import select

    q = select(Cobranca)
    if user.role == UserRole.DONO:
        q = q.where(Cobranca.operacao_id == user.operacao_id)
    elif operacao_scope is not None:
        q = q.where(Cobranca.operacao_id == operacao_scope)
        
    cobs = list(db.scalars(q.order_by(Cobranca.id.desc())).all())
    today = date.today()
    
    # Cache configs da operação (assumindo mesma operacao para a lista)
    op_id = _effective_operacao(user, operacao_scope)
    from motopay.infrastructure.db.models import Operacao
    op_cfg = db.get(Operacao, op_id)
    m_pct = op_cfg.multa_fixa_percentual / Decimal("100")
    j_pct = op_cfg.juros_diario_percentual / Decimal("100")

    for c in cobs:
        if c.status in [CobrancaStatus.PENDENTE.value, CobrancaStatus.ATRASADO.value] and c.vencimento < today:
            dias = (today - c.vencimento).days
            multa = c.valor * m_pct
            juros = c.valor * j_pct * dias
            c.dias_atraso = dias
            c.multa = multa
            c.juros = juros
            c.valor_total = c.valor + multa + juros
            # Forçar status se atrasado
            if c.status == CobrancaStatus.PENDENTE.value:
                c.status = CobrancaStatus.ATRASADO.value
        else:
            c.dias_atraso = 0
            c.multa = Decimal(0)
            c.juros = Decimal(0)
            c.valor_total = c.valor
    return cobs


def handle_payment_confirmed(
    db: Session,
    *,
    asaas_payment_id: str,
    value: Decimal | None = None,
) -> tuple[bool, int | None]:
    """Processa confirmação de pagamento Asaas. Idempotente.

    Retorna (sucesso_encontrou_cobranca, evento_id_para_fila).
    """
    from sqlalchemy import select

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