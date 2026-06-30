from __future__ import annotations

from datetime import date

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, joinedload

from motopay.domain.enums import FinanceiroTipo, UserRole
from motopay.domain.exceptions import ForbiddenError, NotFoundError
from motopay.infrastructure.db.models import Contrato, Financeiro, Moto
from motopay.interfaces.api.deps import CurrentUser
from motopay.interfaces.api.schemas import FinanceiroCreate, FinanceiroUpdate
from motopay.services.labels import locatario_nome, moto_descricao

_SCOPED_ROLES = frozenset({UserRole.DONO})


def _financeiro_query(user: CurrentUser, operacao_scope: int | None) -> Select:
    q = select(Financeiro).options(
        joinedload(Financeiro.moto).joinedload(Moto.contratos).joinedload(Contrato.cliente),
        joinedload(Financeiro.contrato).joinedload(Contrato.cliente),
    )
    if user.role in _SCOPED_ROLES:
        q = q.where(Financeiro.operacao_id == user.operacao_id)
    elif operacao_scope is not None:
        q = q.where(Financeiro.operacao_id == operacao_scope)
    return q


def _enrich(row: Financeiro) -> Financeiro:
    row.moto_descricao = moto_descricao(row.moto)
    row.locatario_nome = locatario_nome(row.contrato, row.moto)
    return row


def list_financeiro(
    db: Session,
    user: CurrentUser,
    operacao_scope: int | None,
    *,
    limit: int,
    offset: int,
    tipo: FinanceiroTipo | None = None,
    moto_id: int | None = None,
    q: str | None = None,
    data_inicio: date | None = None,
    data_fim: date | None = None,
) -> tuple[list[Financeiro], int]:
    base = _financeiro_query(user, operacao_scope)
    if tipo is not None:
        base = base.where(Financeiro.tipo == tipo.value)
    if moto_id is not None:
        base = base.where(Financeiro.moto_id == moto_id)
    if data_inicio is not None:
        base = base.where(Financeiro.data >= data_inicio)
    if data_fim is not None:
        base = base.where(Financeiro.data <= data_fim)
    if q and q.strip():
        term = f"%{q.strip()}%"
        base = base.where(Financeiro.descricao.ilike(term))
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = list(
        db.scalars(
            base.order_by(Financeiro.data.desc(), Financeiro.id.desc()).limit(limit).offset(offset)
        )
        .unique()
        .all()
    )
    for row in rows:
        _enrich(row)
    return rows, int(total)


def get_financeiro(
    db: Session, user: CurrentUser, operacao_scope: int | None, financeiro_id: int
) -> Financeiro:
    row = db.get(Financeiro, financeiro_id)
    if not row:
        raise NotFoundError("Lançamento não encontrado")
    if user.role in _SCOPED_ROLES and row.operacao_id != user.operacao_id:
        raise ForbiddenError("Lançamento fora do escopo")
    if (
        user.role == UserRole.ADMIN
        and operacao_scope is not None
        and row.operacao_id != operacao_scope
    ):
        raise ForbiddenError("Lançamento fora do escopo informado")
    return _enrich(row)


def _validate_relations(
    db: Session, operacao_id: int, moto_id: int | None, contrato_id: int | None
) -> None:
    if moto_id is not None:
        m = db.get(Moto, moto_id)
        if not m or m.operacao_id != operacao_id:
            raise NotFoundError("Moto inválida")
    if contrato_id is not None:
        c = db.get(Contrato, contrato_id)
        if not c or c.operacao_id != operacao_id:
            raise NotFoundError("Contrato inválido")


def create_financeiro(
    db: Session, user: CurrentUser, operacao_scope: int | None, body: FinanceiroCreate
) -> Financeiro:
    operacao_id = operacao_scope if user.role == UserRole.ADMIN else user.operacao_id
    if operacao_id is None:
        raise ForbiddenError("Informe operacao_id")
    _validate_relations(db, operacao_id, body.moto_id, body.contrato_id)
    row = Financeiro(
        operacao_id=operacao_id,
        tipo=body.tipo.value,
        valor=body.valor,
        descricao=body.descricao.strip(),
        data=body.data,
        moto_id=body.moto_id,
        contrato_id=body.contrato_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return get_financeiro(db, user, operacao_scope, row.id)


def update_financeiro(
    db: Session,
    user: CurrentUser,
    operacao_scope: int | None,
    financeiro_id: int,
    body: FinanceiroUpdate,
) -> Financeiro:
    row = get_financeiro(db, user, operacao_scope, financeiro_id)
    moto_id = body.moto_id if body.moto_id is not None else row.moto_id
    contrato_id = body.contrato_id if body.contrato_id is not None else row.contrato_id
    _validate_relations(db, row.operacao_id, moto_id, contrato_id)
    if body.tipo is not None:
        row.tipo = body.tipo.value
    if body.valor is not None:
        row.valor = body.valor
    if body.descricao is not None:
        row.descricao = body.descricao.strip()
    if body.data is not None:
        row.data = body.data
    if body.moto_id is not None:
        row.moto_id = body.moto_id
    if body.contrato_id is not None:
        row.contrato_id = body.contrato_id
    db.add(row)
    db.commit()
    db.refresh(row)
    return get_financeiro(db, user, operacao_scope, row.id)


def delete_financeiro(
    db: Session, user: CurrentUser, operacao_scope: int | None, financeiro_id: int
) -> None:
    from motopay.domain.enums import AnexoEntidade
    from motopay.services.anexo_service import delete_anexos_for_entity

    row = get_financeiro(db, user, operacao_scope, financeiro_id)
    row_id = row.id
    operacao_id = row.operacao_id
    # Apaga anexos (storage + linhas) e o lançamento na MESMA transação — sem órfãos.
    delete_anexos_for_entity(
        db, AnexoEntidade.FINANCEIRO.value, row_id, operacao_id, commit=False
    )
    db.delete(row)
    db.commit()
