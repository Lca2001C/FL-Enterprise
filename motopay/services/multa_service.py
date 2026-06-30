from __future__ import annotations

from datetime import date

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, joinedload

from motopay.domain.enums import AnexoEntidade, MultaStatus, UserRole
from motopay.domain.exceptions import ForbiddenError, NotFoundError
from motopay.infrastructure.db.models import Cliente, Contrato, Moto, Multa
from motopay.interfaces.api.deps import CurrentUser
from motopay.interfaces.api.schemas import MultaCreate, MultaUpdate
from motopay.services.anexo_service import count_anexos, delete_anexos_for_entity
from motopay.services.labels import locatario_nome, moto_descricao

_SCOPED_ROLES = frozenset({UserRole.DONO})


def _multa_query(user: CurrentUser, operacao_scope: int | None) -> Select:
    q = select(Multa).options(
        joinedload(Multa.moto).joinedload(Moto.contratos).joinedload(Contrato.cliente),
        joinedload(Multa.contrato).joinedload(Contrato.cliente),
        joinedload(Multa.cliente),
    )
    if user.role in _SCOPED_ROLES:
        q = q.where(Multa.operacao_id == user.operacao_id)
    elif operacao_scope is not None:
        q = q.where(Multa.operacao_id == operacao_scope)
    return q


def _enrich(db: Session, m: Multa) -> Multa:
    m.moto_descricao = moto_descricao(m.moto)
    fallback = m.cliente.nome if m.cliente is not None else None
    m.locatario_nome = locatario_nome(m.contrato, m.moto) or fallback
    m.total_anexos = count_anexos(db, AnexoEntidade.MULTA.value, m.id)
    return m


def list_multas(
    db: Session,
    user: CurrentUser,
    operacao_scope: int | None,
    *,
    limit: int,
    offset: int,
    status: MultaStatus | None = None,
    moto_id: int | None = None,
    contrato_id: int | None = None,
    q: str | None = None,
    data_inicio: date | None = None,
    data_fim: date | None = None,
) -> tuple[list[Multa], int]:
    base = _multa_query(user, operacao_scope)
    if status is not None:
        base = base.where(Multa.status == status.value)
    if moto_id is not None:
        base = base.where(Multa.moto_id == moto_id)
    if contrato_id is not None:
        base = base.where(Multa.contrato_id == contrato_id)
    if data_inicio is not None:
        base = base.where(Multa.data >= data_inicio)
    if data_fim is not None:
        base = base.where(Multa.data <= data_fim)
    if q and q.strip():
        term = f"%{q.strip()}%"
        base = base.where(or_(Multa.descricao.ilike(term), Multa.orgao.ilike(term)))
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = list(
        db.scalars(
            base.order_by(Multa.data.desc(), Multa.id.desc()).limit(limit).offset(offset)
        )
        .unique()
        .all()
    )
    for m in rows:
        _enrich(db, m)
    return rows, int(total)


def get_multa(
    db: Session, user: CurrentUser, operacao_scope: int | None, multa_id: int
) -> Multa:
    m = db.get(Multa, multa_id)
    if not m:
        raise NotFoundError("Multa não encontrada")
    if user.role in _SCOPED_ROLES and m.operacao_id != user.operacao_id:
        raise ForbiddenError("Multa fora do escopo")
    if (
        user.role == UserRole.ADMIN
        and operacao_scope is not None
        and m.operacao_id != operacao_scope
    ):
        raise ForbiddenError("Multa fora do escopo informado")
    return _enrich(db, m)


def _validate_relations(
    db: Session,
    operacao_id: int,
    moto_id: int | None,
    contrato_id: int | None,
    cliente_id: int | None,
) -> int | None:
    """Valida que moto/contrato/cliente pertencem à operação. Retorna o cliente_id efetivo."""
    if moto_id is not None:
        moto = db.get(Moto, moto_id)
        if not moto or moto.operacao_id != operacao_id:
            raise NotFoundError("Veículo inválido para esta operação")
    contrato = None
    if contrato_id is not None:
        contrato = db.get(Contrato, contrato_id)
        if not contrato or contrato.operacao_id != operacao_id:
            raise NotFoundError("Contrato inválido para esta operação")
    if cliente_id is not None:
        cliente = db.get(Cliente, cliente_id)
        if not cliente or cliente.operacao_id != operacao_id:
            raise NotFoundError("Cliente inválido para esta operação")
    elif contrato is not None:
        cliente_id = contrato.cliente_id
    return cliente_id


def create_multa(
    db: Session, user: CurrentUser, operacao_scope: int | None, body: MultaCreate
) -> Multa:
    operacao_id = operacao_scope if user.role == UserRole.ADMIN else user.operacao_id
    if operacao_id is None:
        raise ForbiddenError("Informe operacao_id")
    cliente_id = _validate_relations(
        db, operacao_id, body.moto_id, body.contrato_id, body.cliente_id
    )
    m = Multa(
        operacao_id=operacao_id,
        moto_id=body.moto_id,
        contrato_id=body.contrato_id,
        cliente_id=cliente_id,
        descricao=body.descricao.strip(),
        orgao=body.orgao.strip() if body.orgao else None,
        valor=body.valor,
        data=body.data,
        vencimento=body.vencimento,
        status=body.status.value,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return get_multa(db, user, operacao_scope, m.id)


def update_multa(
    db: Session,
    user: CurrentUser,
    operacao_scope: int | None,
    multa_id: int,
    body: MultaUpdate,
) -> Multa:
    m = get_multa(db, user, operacao_scope, multa_id)
    moto_id = body.moto_id if body.moto_id is not None else m.moto_id
    contrato_id = body.contrato_id if body.contrato_id is not None else m.contrato_id
    cliente_id = body.cliente_id if body.cliente_id is not None else m.cliente_id
    cliente_id = _validate_relations(db, m.operacao_id, moto_id, contrato_id, cliente_id)

    if body.moto_id is not None:
        m.moto_id = body.moto_id
    if body.contrato_id is not None:
        m.contrato_id = body.contrato_id
    m.cliente_id = cliente_id
    if body.descricao is not None:
        m.descricao = body.descricao.strip()
    if body.orgao is not None:
        m.orgao = body.orgao.strip() if body.orgao else None
    if body.valor is not None:
        m.valor = body.valor
    if body.data is not None:
        m.data = body.data
    if body.vencimento is not None:
        m.vencimento = body.vencimento
    if body.status is not None:
        m.status = body.status.value
    db.add(m)
    db.commit()
    db.refresh(m)
    return get_multa(db, user, operacao_scope, m.id)


def delete_multa(
    db: Session, user: CurrentUser, operacao_scope: int | None, multa_id: int
) -> None:
    m = get_multa(db, user, operacao_scope, multa_id)
    multa_id_val = m.id
    operacao_id = m.operacao_id
    # Apaga anexos (storage + linhas) e a multa na MESMA transação — sem órfãos.
    delete_anexos_for_entity(
        db, AnexoEntidade.MULTA.value, multa_id_val, operacao_id, commit=False
    )
    db.delete(m)
    db.commit()
