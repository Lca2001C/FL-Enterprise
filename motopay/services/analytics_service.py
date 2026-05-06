from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from motopay.domain.enums import FinanceiroTipo, UserRole
from motopay.domain.exceptions import ForbiddenError
from motopay.infrastructure.db.models import Contrato, Financeiro, Moto
from motopay.interfaces.api.deps import CurrentUser
from motopay.interfaces.api.schemas import AnalyticsSummary, MotoAnalyticsRow


def _operacao_filter(user: CurrentUser, operacao_scope: int | None) -> int | None:
    if user.role == UserRole.DONO:
        return user.operacao_id
    return operacao_scope


def get_summary(
    db: Session,
    user: CurrentUser,
    operacao_scope: int | None,
) -> AnalyticsSummary:
    op = _operacao_filter(user, operacao_scope)
    
    # Receita e Despesa
    receita_stmt = select(func.coalesce(func.sum(Financeiro.valor), 0)).where(Financeiro.tipo == FinanceiroTipo.RECEITA.value)
    despesa_stmt = select(func.coalesce(func.sum(Financeiro.valor), 0)).where(Financeiro.tipo == FinanceiroTipo.DESPESA.value)
    
    if user.role == UserRole.DONO:
        receita_stmt = receita_stmt.where(Financeiro.operacao_id == op)
        despesa_stmt = despesa_stmt.where(Financeiro.operacao_id == op)
    elif op is not None:
        receita_stmt = receita_stmt.where(Financeiro.operacao_id == op)
        despesa_stmt = despesa_stmt.where(Financeiro.operacao_id == op)
        
    receita_total = db.scalar(receita_stmt) or Decimal(0)
    despesa_total = db.scalar(despesa_stmt) or Decimal(0)
    
    # Motos Ativas
    from motopay.domain.enums import MotoStatus
    motos_stmt = select(func.count(Moto.id)).where(Moto.status == MotoStatus.ALUGADA.value)
    if user.role == UserRole.DONO:
        motos_stmt = motos_stmt.where(Moto.operacao_id == op)
    elif op is not None:
        motos_stmt = motos_stmt.where(Moto.operacao_id == op)
    motos_ativas = db.scalar(motos_stmt) or 0
    
    # Inadimplentes
    inad_stmt = select(func.count(Contrato.id)).where(Contrato.inadimplente == True)
    if user.role == UserRole.DONO:
        inad_stmt = inad_stmt.where(Contrato.operacao_id == op)
    elif op is not None:
        inad_stmt = inad_stmt.where(Contrato.operacao_id == op)
    inadimplentes = db.scalar(inad_stmt) or 0
    
    # Cobrancas Stats
    from motopay.infrastructure.db.models import Cobranca
    from motopay.domain.enums import CobrancaStatus
    
    cob_stmt = select(
        func.count(Cobranca.id),
        func.count(case((Cobranca.status == CobrancaStatus.PENDENTE.value, 1))),
        func.count(case((Cobranca.status == CobrancaStatus.ATRASADO.value, 1)))
    )
    if user.role == UserRole.DONO:
        cob_stmt = cob_stmt.where(Cobranca.operacao_id == op)
    elif op is not None:
        cob_stmt = cob_stmt.where(Cobranca.operacao_id == op)
        
    total_cob, pendentes, atrasadas = db.execute(cob_stmt).first() or (0, 0, 0)

    return AnalyticsSummary(
        receita_total=receita_total,
        despesa_total=despesa_total,
        lucro_liquido=receita_total - despesa_total,
        motos_ativas=int(motos_ativas),
        clientes_inadimplentes=int(inadimplentes),
        total_cobrancas=int(total_cob),
        cobrancas_pendentes=int(pendentes),
        cobrancas_atrasadas=int(atrasadas)
    )


def moto_ranking(
    db: Session,
    user: CurrentUser,
    operacao_scope: int | None,
    data_inicio: date,
    data_fim: date,
) -> list[MotoAnalyticsRow]:
    op = _operacao_filter(user, operacao_scope)
    if user.role == UserRole.DONO and op is None:
        raise ForbiddenError("Operação não definida")
    receita_expr = func.coalesce(
        func.sum(case((Financeiro.tipo == FinanceiroTipo.RECEITA.value, Financeiro.valor), else_=0)),
        0,
    )
    despesa_expr = func.coalesce(
        func.sum(case((Financeiro.tipo == FinanceiroTipo.DESPESA.value, Financeiro.valor), else_=0)),
        0,
    )
    stmt = (
        select(Moto.id, Moto.placa, Moto.modelo, receita_expr, despesa_expr)
        .select_from(Moto)
        .outerjoin(
            Financeiro,
            (Financeiro.moto_id == Moto.id)
            & (Financeiro.data >= data_inicio)
            & (Financeiro.data <= data_fim),
        )
        .group_by(Moto.id, Moto.placa, Moto.modelo)
    )
    if user.role == UserRole.DONO:
        stmt = stmt.where(Moto.operacao_id == op)
    elif op is not None:
        stmt = stmt.where(Moto.operacao_id == op)
    rows_raw = db.execute(stmt).all()
    out: list[MotoAnalyticsRow] = []
    for mid, placa, modelo, rec, des in rows_raw:
        rec_d = Decimal(rec or 0)
        des_d = Decimal(des or 0)
        lucro = rec_d - des_d
        roi: Decimal | None
        if des_d > 0:
            roi = lucro / des_d
        else:
            roi = None
        out.append(
            MotoAnalyticsRow(
                moto_id=int(mid),
                placa=str(placa),
                modelo=str(modelo),
                receita=rec_d,
                despesa=des_d,
                lucro_liquido=lucro,
                roi=roi,
                prejuizo=lucro < 0,
            )
        )
    out.sort(key=lambda r: r.lucro_liquido, reverse=True)
    return out


def get_recent_activity(
    db: Session,
    user: CurrentUser,
    operacao_scope: int | None,
    limit: int = 10,
) -> list[RecentActivityRow]:
    from motopay.interfaces.api.schemas import RecentActivityRow
    
    op = _operacao_filter(user, operacao_scope)
    stmt = select(Financeiro).order_by(Financeiro.data.desc(), Financeiro.created_at.desc()).limit(limit)
    
    if user.role == UserRole.DONO:
        stmt = stmt.where(Financeiro.operacao_id == op)
    elif op is not None:
        stmt = stmt.where(Financeiro.operacao_id == op)
        
    rows = db.scalars(stmt).all()
    return [
        RecentActivityRow(
            id=r.id,
            tipo=r.tipo,
            descricao=r.descricao,
            data=r.data,
            valor=r.valor
        ) for r in rows
    ]
