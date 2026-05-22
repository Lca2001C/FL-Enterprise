from __future__ import annotations

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from motopay.domain.enums import ContratoStatus, DomainEventType, MotoStatus, UserRole
from motopay.domain.exceptions import ConflictError, ForbiddenError, NotFoundError
from motopay.infrastructure.db.models import Cliente, Contrato, EventoDominio, Moto
from motopay.interfaces.api.deps import CurrentUser
from motopay.interfaces.api.schemas import (
    ClienteCreate,
    ClienteUpdate,
    ContratoCreate,
    ContratoUpdate,
    MotoCreate,
    MotoUpdate,
)

_SCOPED_ROLES = frozenset({UserRole.DONO, UserRole.OPERADOR})


def _moto_query(user: CurrentUser, operacao_scope: int | None) -> Select:
    from sqlalchemy.orm import joinedload

    q = select(Moto).options(joinedload(Moto.contratos).joinedload(Contrato.cliente))
    if user.role in _SCOPED_ROLES:
        q = q.where(Moto.operacao_id == user.operacao_id)
    elif operacao_scope is not None:
        q = q.where(Moto.operacao_id == operacao_scope)
    return q


def list_motos(
    db: Session,
    user: CurrentUser,
    operacao_scope: int | None,
    *,
    limit: int,
    offset: int,
    status: MotoStatus | None = None,
    q: str | None = None,
) -> tuple[list[Moto], int]:
    base = _moto_query(user, operacao_scope)
    if status is not None:
        base = base.where(Moto.status == status.value)
    if q and q.strip():
        term = f"%{q.strip()}%"
        base = base.where(or_(Moto.placa.ilike(term), Moto.modelo.ilike(term)))
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    motos = list(db.scalars(base.order_by(Moto.id).limit(limit).offset(offset)).all())
    for m in motos:
        active_ct = next(
            (ct for ct in m.contratos if ct.status == ContratoStatus.ATIVO.value), None
        )
        if active_ct:
            m.cliente_nome = active_ct.cliente.nome
    return motos, int(total)


def get_moto(db: Session, user: CurrentUser, operacao_scope: int | None, moto_id: int) -> Moto:
    m = db.get(Moto, moto_id)
    if not m:
        raise NotFoundError("Moto não encontrada")
    if user.role in _SCOPED_ROLES and m.operacao_id != user.operacao_id:
        raise ForbiddenError("Moto fora do escopo")
    if (
        user.role == UserRole.ADMIN
        and operacao_scope is not None
        and m.operacao_id != operacao_scope
    ):
        raise ForbiddenError("Moto fora do escopo informado")
    return m


def create_moto(
    db: Session, user: CurrentUser, operacao_scope: int | None, body: MotoCreate
) -> Moto:
    operacao_id = operacao_scope if user.role == UserRole.ADMIN else user.operacao_id
    if operacao_id is None:
        raise ForbiddenError("Informe operacao_id")
    exists = db.scalars(
        select(Moto).where(Moto.operacao_id == operacao_id, Moto.placa == body.placa.upper())
    ).first()
    if exists:
        raise ConflictError("Placa já cadastrada nesta operação")
    m = Moto(
        operacao_id=operacao_id,
        placa=body.placa.upper().strip(),
        modelo=body.modelo.strip(),
        status=body.status.value,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


def update_moto(
    db: Session, user: CurrentUser, operacao_scope: int | None, moto_id: int, body: MotoUpdate
) -> Moto:
    m = get_moto(db, user, operacao_scope, moto_id)
    old_status = m.status
    if body.placa is not None:
        placa = body.placa.upper().strip()
        clash = db.scalars(
            select(Moto).where(
                Moto.operacao_id == m.operacao_id, Moto.placa == placa, Moto.id != m.id
            )
        ).first()
        if clash:
            raise ConflictError("Placa já cadastrada nesta operação")
        m.placa = placa
    if body.modelo is not None:
        m.modelo = body.modelo.strip()
    if body.status is not None:
        m.status = body.status.value
    db.add(m)
    db.commit()
    db.refresh(m)
    if (
        body.status is not None
        and m.status == MotoStatus.MANUTENCAO.value
        and old_status != MotoStatus.MANUTENCAO.value
    ):
        from motopay.infrastructure.messaging.tasks import handle_domain_event

        ev = EventoDominio(
            tipo=DomainEventType.MOTO_EM_MANUTENCAO.value,
            payload={"moto_id": m.id, "operacao_id": m.operacao_id},
        )
        db.add(ev)
        db.commit()
        db.refresh(ev)
        handle_domain_event.delay(ev.id)
    return m


def _cliente_query(user: CurrentUser, operacao_scope: int | None) -> Select:
    from sqlalchemy.orm import joinedload

    q = select(Cliente).options(joinedload(Cliente.contratos).joinedload(Contrato.moto))
    if user.role in _SCOPED_ROLES:
        q = q.where(Cliente.operacao_id == user.operacao_id)
    elif operacao_scope is not None:
        q = q.where(Cliente.operacao_id == operacao_scope)
    return q


def list_clientes(
    db: Session,
    user: CurrentUser,
    operacao_scope: int | None,
    *,
    limit: int,
    offset: int,
    q: str | None = None,
) -> tuple[list[Cliente], int]:
    base = _cliente_query(user, operacao_scope)
    if q and q.strip():
        term = f"%{q.strip()}%"
        base = base.where(or_(Cliente.nome.ilike(term), Cliente.cpf.ilike(term)))
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    clientes = list(db.scalars(base.order_by(Cliente.id).limit(limit).offset(offset)).all())
    for c in clientes:
        active_ct = next(
            (ct for ct in c.contratos if ct.status == ContratoStatus.ATIVO.value), None
        )
        if active_ct:
            c.moto_placa = active_ct.moto.placa
            c.moto_modelo = active_ct.moto.modelo
    return clientes, int(total)


def get_cliente(
    db: Session, user: CurrentUser, operacao_scope: int | None, cliente_id: int
) -> Cliente:
    c = db.get(Cliente, cliente_id)
    if not c:
        raise NotFoundError("Cliente não encontrado")
    if user.role in _SCOPED_ROLES and c.operacao_id != user.operacao_id:
        raise ForbiddenError("Cliente fora do escopo")
    if (
        user.role == UserRole.ADMIN
        and operacao_scope is not None
        and c.operacao_id != operacao_scope
    ):
        raise ForbiddenError("Cliente fora do escopo informado")
    return c


def create_cliente(
    db: Session, user: CurrentUser, operacao_scope: int | None, body: ClienteCreate
) -> Cliente:
    operacao_id = operacao_scope if user.role == UserRole.ADMIN else user.operacao_id
    if operacao_id is None:
        raise ForbiddenError("Informe operacao_id")
    cpf = body.cpf.strip()
    exists = db.scalars(
        select(Cliente).where(Cliente.operacao_id == operacao_id, Cliente.cpf == cpf)
    ).first()
    if exists:
        raise ConflictError("CPF já cadastrado nesta operação")
    c = Cliente(
        operacao_id=operacao_id,
        nome=body.nome.strip(),
        cpf=cpf,
        telefone=body.telefone.strip(),
        telegram_id=body.telegram_id.strip() if body.telegram_id else None,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def update_cliente(
    db: Session, user: CurrentUser, operacao_scope: int | None, cliente_id: int, body: ClienteUpdate
) -> Cliente:
    c = get_cliente(db, user, operacao_scope, cliente_id)
    if body.nome is not None:
        c.nome = body.nome.strip()
    if body.telefone is not None:
        c.telefone = body.telefone.strip()
    if body.telegram_id is not None:
        c.telegram_id = body.telegram_id.strip() if body.telegram_id else None
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def delete_cliente(db: Session, user: CurrentUser, operacao_scope: int | None, cliente_id: int):
    c = get_cliente(db, user, operacao_scope, cliente_id)
    db.delete(c)
    db.commit()


def list_contratos(
    db: Session,
    user: CurrentUser,
    operacao_scope: int | None,
    *,
    limit: int,
    offset: int,
    com_promessa: bool | None = None,
    status: ContratoStatus | None = None,
    inadimplente: bool | None = None,
    cliente_id: int | None = None,
) -> tuple[list[Contrato], int]:
    q = select(Contrato)
    if user.role in _SCOPED_ROLES:
        q = q.where(Contrato.operacao_id == user.operacao_id)
    elif operacao_scope is not None:
        q = q.where(Contrato.operacao_id == operacao_scope)
    if com_promessa is True:
        q = q.where(Contrato.promessa_pagamento_em.isnot(None))
    if status is not None:
        q = q.where(Contrato.status == status.value)
    if inadimplente is not None:
        q = q.where(Contrato.inadimplente.is_(inadimplente))
    if cliente_id is not None:
        q = q.where(Contrato.cliente_id == cliente_id)
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = list(db.scalars(q.order_by(Contrato.id).limit(limit).offset(offset)).all())
    return rows, int(total)


def get_contrato(
    db: Session, user: CurrentUser, operacao_scope: int | None, contrato_id: int
) -> Contrato:
    ct = db.get(Contrato, contrato_id)
    if not ct:
        raise NotFoundError("Contrato não encontrado")
    if user.role in _SCOPED_ROLES and ct.operacao_id != user.operacao_id:
        raise ForbiddenError("Contrato fora do escopo")
    if (
        user.role == UserRole.ADMIN
        and operacao_scope is not None
        and ct.operacao_id != operacao_scope
    ):
        raise ForbiddenError("Contrato fora do escopo informado")
    return ct


def create_contrato(
    db: Session, user: CurrentUser, operacao_scope: int | None, body: ContratoCreate
) -> Contrato:
    operacao_id = operacao_scope if user.role == UserRole.ADMIN else user.operacao_id
    if operacao_id is None:
        raise ForbiddenError("Informe operacao_id")
    cliente = db.get(Cliente, body.cliente_id)
    if not cliente or cliente.operacao_id != operacao_id:
        raise NotFoundError("Cliente inválido para esta operação")
    moto = db.get(Moto, body.moto_id)
    if not moto or moto.operacao_id != operacao_id:
        raise NotFoundError("Moto inválida para esta operação")
    ct = Contrato(
        operacao_id=operacao_id,
        cliente_id=body.cliente_id,
        moto_id=body.moto_id,
        valor_recorrente=body.valor_recorrente,
        ciclo=body.ciclo.value,
        status=body.status.value,
        data_inicio=body.data_inicio,
        proximo_vencimento=body.proximo_vencimento,
    )
    db.add(ct)
    moto.status = MotoStatus.ALUGADA.value
    db.add(moto)
    db.commit()
    db.refresh(ct)
    return ct


def update_contrato(
    db: Session,
    user: CurrentUser,
    operacao_scope: int | None,
    contrato_id: int,
    body: ContratoUpdate,
) -> Contrato:
    ct = get_contrato(db, user, operacao_scope, contrato_id)
    if body.status is not None:
        ct.status = body.status.value
    if body.valor_recorrente is not None:
        ct.valor_recorrente = body.valor_recorrente
    if body.proximo_vencimento is not None:
        ct.proximo_vencimento = body.proximo_vencimento
    db.add(ct)
    db.commit()
    db.refresh(ct)
    return ct
