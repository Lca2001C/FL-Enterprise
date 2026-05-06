from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from motopay.domain.enums import FinanceiroTipo, UserRole
from motopay.domain.exceptions import ForbiddenError
from motopay.infrastructure.db.models import Financeiro, Moto
from motopay.interfaces.api.deps import CurrentUser
from motopay.interfaces.api.schemas import MotoAnalyticsRow


def _operacao_filter(user: CurrentUser, operacao_scope: int | None) -> int | None:
    if user.role == UserRole.DONO:
        return user.operacao_id
    return operacao_scope


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
