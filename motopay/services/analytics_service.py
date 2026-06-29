from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session, aliased

from motopay.config import app_today
from motopay.domain.enums import CobrancaStatus, FinanceiroTipo, MotoStatus, UserRole
from motopay.domain.exceptions import ForbiddenError
from motopay.infrastructure.db.models import Cliente, Cobranca, Contrato, Financeiro, Moto
from motopay.interfaces.api.deps import CurrentUser
from motopay.interfaces.api.schemas import (
    AnalyticsSummary,
    DashboardInadimplenciaItem,
    MotoAnalyticsRow,
    RecentActivityRow,
)


def _operacao_filter(user: CurrentUser, operacao_scope: int | None) -> int | None:
    if user.role == UserRole.DONO:
        return user.operacao_id
    return operacao_scope


def _scope_where_cobranca(user: CurrentUser, op: int | None):
    if user.role == UserRole.DONO:
        return Cobranca.operacao_id == op
    if op is not None:
        return Cobranca.operacao_id == op
    return None


def _scope_where_financeiro(user: CurrentUser, op: int | None):
    if user.role == UserRole.DONO:
        return Financeiro.operacao_id == op
    if op is not None:
        return Financeiro.operacao_id == op
    return None


def _scope_where_moto(user: CurrentUser, op: int | None):
    if user.role == UserRole.DONO:
        return Moto.operacao_id == op
    if op is not None:
        return Moto.operacao_id == op
    return None


def _scope_where_contrato(user: CurrentUser, op: int | None):
    if user.role == UserRole.DONO:
        return Contrato.operacao_id == op
    if op is not None:
        return Contrato.operacao_id == op
    return None


def get_summary(
    db: Session,
    user: CurrentUser,
    operacao_scope: int | None,
) -> AnalyticsSummary:
    op = _operacao_filter(user, operacao_scope)
    today = app_today()

    receita_stmt = select(func.coalesce(func.sum(Financeiro.valor), 0)).where(
        Financeiro.tipo == FinanceiroTipo.RECEITA.value
    )
    despesa_stmt = select(func.coalesce(func.sum(Financeiro.valor), 0)).where(
        Financeiro.tipo == FinanceiroTipo.DESPESA.value
    )
    sf = _scope_where_financeiro(user, op)
    if sf is not None:
        receita_stmt = receita_stmt.where(sf)
        despesa_stmt = despesa_stmt.where(sf)

    receita_total = Decimal(db.scalar(receita_stmt) or 0)
    despesa_total = Decimal(db.scalar(despesa_stmt) or 0)

    motos_stmt = select(func.count(Moto.id)).where(Moto.status == MotoStatus.ALUGADA.value)
    sm = _scope_where_moto(user, op)
    if sm is not None:
        motos_stmt = motos_stmt.where(sm)
    motos_ativas = int(db.scalar(motos_stmt) or 0)

    inad_stmt = select(func.count(Contrato.id)).where(Contrato.inadimplente.is_(True))
    sc = _scope_where_contrato(user, op)
    if sc is not None:
        inad_stmt = inad_stmt.where(sc)
    inadimplentes = int(db.scalar(inad_stmt) or 0)

    cob_base = select(func.count(Cobranca.id))
    sw = _scope_where_cobranca(user, op)
    if sw is not None:
        cob_base = cob_base.where(sw)
    total_cob = int(db.scalar(cob_base) or 0)

    pendentes_stmt = select(func.count(Cobranca.id)).where(
        Cobranca.status == CobrancaStatus.PENDENTE.value,
        Cobranca.vencimento >= today,
    )
    if sw is not None:
        pendentes_stmt = pendentes_stmt.where(sw)
    pendentes = int(db.scalar(pendentes_stmt) or 0)

    atrasadas_stmt = select(func.count(Cobranca.id)).where(
        or_(
            Cobranca.status == CobrancaStatus.ATRASADO.value,
            and_(Cobranca.status == CobrancaStatus.PENDENTE.value, Cobranca.vencimento < today),
        )
    )
    if sw is not None:
        atrasadas_stmt = atrasadas_stmt.where(sw)
    atrasadas = int(db.scalar(atrasadas_stmt) or 0)

    return AnalyticsSummary(
        receita_total=receita_total,
        despesa_total=despesa_total,
        lucro_liquido=receita_total - despesa_total,
        motos_ativas=motos_ativas,
        clientes_inadimplentes=inadimplentes,
        total_cobrancas=total_cob,
        cobrancas_pendentes=pendentes,
        cobrancas_atrasadas=atrasadas,
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
        func.sum(
            case((Financeiro.tipo == FinanceiroTipo.RECEITA.value, Financeiro.valor), else_=0)
        ),
        0,
    )
    despesa_expr = func.coalesce(
        func.sum(
            case((Financeiro.tipo == FinanceiroTipo.DESPESA.value, Financeiro.valor), else_=0)
        ),
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


def get_dashboard_inadimplencia(
    db: Session,
    user: CurrentUser,
    operacao_scope: int | None,
    limit: int = 5,
) -> list[DashboardInadimplenciaItem]:
    """Retorna os N contratos mais inadimplentes com nome do cliente e Pix já embutidos.

    Usa uma única query com subquery correlacionada para evitar N+1 e eliminando a
    necessidade de o dashboard carregar todos os clientes e cobranças em memória.
    """
    op = _operacao_filter(user, operacao_scope)

    _OPEN = (CobrancaStatus.PENDENTE.value, CobrancaStatus.ATRASADO.value)

    # Subquery: id da cobrança mais recente e aberta de cada contrato
    latest_cob_id = (
        select(func.max(Cobranca.id))
        .where(
            Cobranca.contrato_id == Contrato.id,
            Cobranca.status.in_(_OPEN),
        )
        .correlate(Contrato)
        .scalar_subquery()
    )

    CobAlias = aliased(Cobranca)

    stmt = (
        select(
            Contrato.id,
            Cliente.nome,
            Contrato.dias_atraso_acumulado,
            Contrato.proximo_vencimento,
            CobAlias.pix_copia_cola,
        )
        .join(Cliente, Cliente.id == Contrato.cliente_id)
        .outerjoin(CobAlias, CobAlias.id == latest_cob_id)
        .where(Contrato.inadimplente.is_(True))
        .order_by(Contrato.dias_atraso_acumulado.desc())
        .limit(limit)
    )

    sc = _scope_where_contrato(user, op)
    if sc is not None:
        stmt = stmt.where(sc)

    rows = db.execute(stmt).all()
    return [
        DashboardInadimplenciaItem(
            contrato_id=row[0],
            cliente_nome=row[1],
            dias_atraso=row[2],
            proximo_vencimento=row[3],
            pix_copia_cola=row[4],
        )
        for row in rows
    ]


def get_recent_activity(
    db: Session,
    user: CurrentUser,
    operacao_scope: int | None,
    limit: int = 10,
) -> list[RecentActivityRow]:
    op = _operacao_filter(user, operacao_scope)
    stmt = select(Financeiro)
    sf = _scope_where_financeiro(user, op)
    if sf is not None:
        stmt = stmt.where(sf)
    stmt = stmt.order_by(Financeiro.data.desc(), Financeiro.created_at.desc()).limit(limit)
    rows = db.scalars(stmt).all()
    return [
        RecentActivityRow(
            id=r.id,
            tipo=r.tipo,
            descricao=r.descricao,
            data=r.data,
            valor=r.valor,
        )
        for r in rows
    ]
