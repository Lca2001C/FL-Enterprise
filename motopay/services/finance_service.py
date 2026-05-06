from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from motopay.domain.enums import UserRole
from motopay.domain.exceptions import ForbiddenError, NotFoundError
from motopay.infrastructure.db.models import Contrato, Financeiro, Moto
from motopay.interfaces.api.deps import CurrentUser
from motopay.interfaces.api.schemas import FinanceiroCreate


def list_financeiro(db: Session, user: CurrentUser, operacao_scope: int | None) -> list[Financeiro]:
    q = select(Financeiro)
    if user.role == UserRole.DONO:
        q = q.where(Financeiro.operacao_id == user.operacao_id)
    elif operacao_scope is not None:
        q = q.where(Financeiro.operacao_id == operacao_scope)
    return list(db.scalars(q.order_by(Financeiro.data.desc(), Financeiro.id.desc())).all())


def create_financeiro(db: Session, user: CurrentUser, operacao_scope: int | None, body: FinanceiroCreate) -> Financeiro:
    operacao_id = operacao_scope if user.role == UserRole.ADMIN else user.operacao_id
    if operacao_id is None:
        raise ForbiddenError("Informe operacao_id")
    if body.moto_id is not None:
        m = db.get(Moto, body.moto_id)
        if not m or m.operacao_id != operacao_id:
            raise NotFoundError("Moto inválida")
    if body.contrato_id is not None:
        c = db.get(Contrato, body.contrato_id)
        if not c or c.operacao_id != operacao_id:
            raise NotFoundError("Contrato inválido")
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
    return row
