from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Select, case, func, select
from sqlalchemy.orm import Session, joinedload

from motopay.domain.enums import (
    FinanceiroCategoria,
    FinanceiroTipo,
    ManutencaoCausa,
    ManutencaoTipo,
    UserRole,
)
from motopay.domain.exceptions import ForbiddenError, NotFoundError
from motopay.infrastructure.db.models import Financeiro, Manutencao, Moto
from motopay.interfaces.api.deps import CurrentUser
from motopay.interfaces.api.schemas import (
    ManutencaoCreate,
    ManutencaoMotoResumo,
    ManutencaoResumoOut,
    ManutencaoUpdate,
)
from motopay.services.labels import moto_descricao

_SCOPED_ROLES = frozenset({UserRole.DONO})

_TIPO_LABELS = {
    ManutencaoTipo.PREVENTIVA.value: "preventiva",
    ManutencaoTipo.CORRETIVA.value: "corretiva",
}


def _despesa_descricao(m: Manutencao) -> str:
    """Descrição da despesa espelho no financeiro (máx. 512, igual à coluna)."""
    tipo = _TIPO_LABELS.get(m.tipo, m.tipo)
    return f"Manutenção {tipo}: {m.descricao}"[:512]


def _manutencao_query(user: CurrentUser, operacao_scope: int | None) -> Select:
    q = select(Manutencao).options(joinedload(Manutencao.moto))
    if user.role in _SCOPED_ROLES:
        q = q.where(Manutencao.operacao_id == user.operacao_id)
    elif operacao_scope is not None:
        q = q.where(Manutencao.operacao_id == operacao_scope)
    return q


def _enrich(row: Manutencao) -> Manutencao:
    row.moto_descricao = moto_descricao(row.moto)
    return row


def _apply_filters(
    base: Select,
    *,
    tipo: ManutencaoTipo | None = None,
    causa: ManutencaoCausa | None = None,
    moto_id: int | None = None,
    q: str | None = None,
    data_inicio: date | None = None,
    data_fim: date | None = None,
) -> Select:
    if tipo is not None:
        base = base.where(Manutencao.tipo == tipo.value)
    if causa is not None:
        base = base.where(Manutencao.causa == causa.value)
    if moto_id is not None:
        base = base.where(Manutencao.moto_id == moto_id)
    if data_inicio is not None:
        base = base.where(Manutencao.data >= data_inicio)
    if data_fim is not None:
        base = base.where(Manutencao.data <= data_fim)
    if q and q.strip():
        term = f"%{q.strip()}%"
        base = base.where(Manutencao.descricao.ilike(term))
    return base


def list_manutencoes(
    db: Session,
    user: CurrentUser,
    operacao_scope: int | None,
    *,
    limit: int,
    offset: int,
    tipo: ManutencaoTipo | None = None,
    causa: ManutencaoCausa | None = None,
    moto_id: int | None = None,
    q: str | None = None,
    data_inicio: date | None = None,
    data_fim: date | None = None,
) -> tuple[list[Manutencao], int]:
    base = _apply_filters(
        _manutencao_query(user, operacao_scope),
        tipo=tipo,
        causa=causa,
        moto_id=moto_id,
        q=q,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = list(
        db.scalars(
            base.order_by(Manutencao.data.desc(), Manutencao.id.desc())
            .limit(limit)
            .offset(offset)
        )
        .unique()
        .all()
    )
    for row in rows:
        _enrich(row)
    return rows, int(total)


def get_manutencao(
    db: Session, user: CurrentUser, operacao_scope: int | None, manutencao_id: int
) -> Manutencao:
    row = db.get(Manutencao, manutencao_id)
    if not row:
        raise NotFoundError("Manutenção não encontrada")
    if user.role in _SCOPED_ROLES and row.operacao_id != user.operacao_id:
        raise ForbiddenError("Manutenção fora do escopo")
    if (
        user.role == UserRole.ADMIN
        and operacao_scope is not None
        and row.operacao_id != operacao_scope
    ):
        raise ForbiddenError("Manutenção fora do escopo informado")
    return _enrich(row)


def _validate_moto(db: Session, operacao_id: int, moto_id: int) -> Moto:
    moto = db.get(Moto, moto_id)
    if not moto or moto.operacao_id != operacao_id:
        raise NotFoundError("Veículo inválido para esta operação")
    return moto


def _sync_despesa(db: Session, m: Manutencao) -> None:
    """Garante que a despesa espelho no financeiro exista e reflita a manutenção.

    Recria a despesa se o vínculo tiver sido perdido (ex.: linha apagada por
    rotina externa). Não faz commit — participa da transação do chamador.
    """
    despesa: Financeiro | None = None
    if m.financeiro_id is not None:
        despesa = db.get(Financeiro, m.financeiro_id)
    if despesa is None:
        despesa = Financeiro(
            operacao_id=m.operacao_id,
            tipo=FinanceiroTipo.DESPESA.value,
            categoria=FinanceiroCategoria.MANUTENCAO.value,
            valor=m.valor,
            descricao=_despesa_descricao(m),
            data=m.data,
            moto_id=m.moto_id,
        )
        db.add(despesa)
        db.flush()
        m.financeiro_id = despesa.id
        return
    despesa.tipo = FinanceiroTipo.DESPESA.value
    despesa.categoria = FinanceiroCategoria.MANUTENCAO.value
    despesa.valor = m.valor
    despesa.descricao = _despesa_descricao(m)
    despesa.data = m.data
    despesa.moto_id = m.moto_id


def create_manutencao(
    db: Session, user: CurrentUser, operacao_scope: int | None, body: ManutencaoCreate
) -> Manutencao:
    operacao_id = operacao_scope if user.role == UserRole.ADMIN else user.operacao_id
    if operacao_id is None:
        raise ForbiddenError("Informe operacao_id")
    _validate_moto(db, operacao_id, body.moto_id)
    row = Manutencao(
        operacao_id=operacao_id,
        moto_id=body.moto_id,
        tipo=body.tipo.value,
        descricao=body.descricao.strip(),
        causa=body.causa.value,
        valor=body.valor,
        data=body.data,
        km=body.km,
    )
    db.add(row)
    db.flush()
    # Manutenção e despesa nascem na MESMA transação — sem divergência.
    _sync_despesa(db, row)
    db.commit()
    db.refresh(row)
    return get_manutencao(db, user, operacao_scope, row.id)


def update_manutencao(
    db: Session,
    user: CurrentUser,
    operacao_scope: int | None,
    manutencao_id: int,
    body: ManutencaoUpdate,
) -> Manutencao:
    row = get_manutencao(db, user, operacao_scope, manutencao_id)
    if body.moto_id is not None:
        _validate_moto(db, row.operacao_id, body.moto_id)
        row.moto_id = body.moto_id
    if body.tipo is not None:
        row.tipo = body.tipo.value
    if body.descricao is not None:
        row.descricao = body.descricao.strip()
    if body.causa is not None:
        row.causa = body.causa.value
    if body.valor is not None:
        row.valor = body.valor
    if body.data is not None:
        row.data = body.data
    if body.km is not None:
        row.km = body.km
    _sync_despesa(db, row)
    db.add(row)
    db.commit()
    db.refresh(row)
    return get_manutencao(db, user, operacao_scope, row.id)


def delete_manutencao(
    db: Session, user: CurrentUser, operacao_scope: int | None, manutencao_id: int
) -> None:
    row = get_manutencao(db, user, operacao_scope, manutencao_id)
    despesa = db.get(Financeiro, row.financeiro_id) if row.financeiro_id is not None else None
    # Defesa em profundidade: só apaga a despesa espelho se ela for da MESMA operação.
    if despesa is not None and despesa.operacao_id != row.operacao_id:
        raise ForbiddenError("Despesa vinculada fora do escopo da operação")
    # Desfaz o vínculo antes de apagar a despesa (FK manutencoes.financeiro_id).
    row.financeiro_id = None
    db.flush()
    if despesa is not None:
        db.delete(despesa)
    db.delete(row)
    db.commit()


def resumo_manutencoes(
    db: Session,
    user: CurrentUser,
    operacao_scope: int | None,
    *,
    tipo: ManutencaoTipo | None = None,
    causa: ManutencaoCausa | None = None,
    moto_id: int | None = None,
    q: str | None = None,
    data_inicio: date | None = None,
    data_fim: date | None = None,
) -> ManutencaoResumoOut:
    """Totais de manutenção (geral, por tipo, por causa e por moto) com os
    mesmos filtros da listagem — alimenta o dashboard e o PDF de manutenções."""
    op_filter: Select = select(Manutencao)
    if user.role in _SCOPED_ROLES:
        op_filter = op_filter.where(Manutencao.operacao_id == user.operacao_id)
    elif operacao_scope is not None:
        op_filter = op_filter.where(Manutencao.operacao_id == operacao_scope)
    filtered = _apply_filters(
        op_filter,
        tipo=tipo,
        causa=causa,
        moto_id=moto_id,
        q=q,
        data_inicio=data_inicio,
        data_fim=data_fim,
    ).subquery()

    total_geral, quantidade, total_prev, total_corr = db.execute(
        select(
            func.coalesce(func.sum(filtered.c.valor), 0),
            func.count(filtered.c.id),
            func.coalesce(
                func.sum(
                    case(
                        (filtered.c.tipo == ManutencaoTipo.PREVENTIVA.value, filtered.c.valor),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case(
                        (filtered.c.tipo == ManutencaoTipo.CORRETIVA.value, filtered.c.valor),
                        else_=0,
                    )
                ),
                0,
            ),
        )
    ).one()

    por_moto_rows = db.execute(
        select(
            Moto.id,
            Moto.placa,
            Moto.modelo,
            func.coalesce(func.sum(filtered.c.valor), 0),
            func.count(filtered.c.id),
        )
        .join(filtered, filtered.c.moto_id == Moto.id)
        .group_by(Moto.id, Moto.placa, Moto.modelo)
        .order_by(func.coalesce(func.sum(filtered.c.valor), 0).desc())
    ).all()

    por_causa_rows = db.execute(
        select(filtered.c.causa, func.coalesce(func.sum(filtered.c.valor), 0)).group_by(
            filtered.c.causa
        )
    ).all()

    q2 = Decimal("0.01")
    return ManutencaoResumoOut(
        total_geral=Decimal(total_geral or 0).quantize(q2),
        quantidade=int(quantidade or 0),
        total_preventiva=Decimal(total_prev or 0).quantize(q2),
        total_corretiva=Decimal(total_corr or 0).quantize(q2),
        por_moto=[
            ManutencaoMotoResumo(
                moto_id=int(mid),
                placa=str(placa),
                modelo=str(modelo),
                total=Decimal(tot or 0).quantize(q2),
                quantidade=int(qtd or 0),
            )
            for mid, placa, modelo, tot, qtd in por_moto_rows
        ],
        por_causa={str(c): Decimal(v or 0).quantize(q2) for c, v in por_causa_rows},
    )
