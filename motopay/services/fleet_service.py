from __future__ import annotations

import logging

from sqlalchemy import Select, delete, func, or_, select, update
from sqlalchemy.orm import Session

from motopay.domain.enums import ContratoStatus, DomainEventType, MotoStatus, UserRole
from motopay.domain.exceptions import ConflictError, ForbiddenError, NotFoundError
from motopay.infrastructure.db.models import (
    Cliente,
    Cobranca,
    Contrato,
    EventoDominio,
    Financeiro,
    Moto,
    Multa,
)
from motopay.interfaces.api.deps import CurrentUser
from motopay.interfaces.api.schemas import (
    ClienteCreate,
    ClienteUpdate,
    ContratoCreate,
    ContratoUpdate,
    MotoCreate,
    MotoUpdate,
)

logger = logging.getLogger(__name__)

_SCOPED_ROLES = frozenset({UserRole.DONO})


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
    motos = list(db.scalars(base.order_by(Moto.id).limit(limit).offset(offset)).unique().all())
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
        raise NotFoundError("Veículo não encontrado")
    if user.role in _SCOPED_ROLES and m.operacao_id != user.operacao_id:
        raise ForbiddenError("Veículo fora do escopo")
    if (
        user.role == UserRole.ADMIN
        and operacao_scope is not None
        and m.operacao_id != operacao_scope
    ):
        raise ForbiddenError("Veículo fora do escopo informado")
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
        ano=body.ano,
        cor=body.cor.strip() if body.cor else None,
        tipo=body.tipo.value,
        status=body.status.value,
        km=body.km,
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
    if body.ano is not None:
        m.ano = body.ano
    if body.cor is not None:
        m.cor = body.cor.strip() or None
    if body.tipo is not None:
        m.tipo = body.tipo.value
    if body.status is not None:
        m.status = body.status.value
    if body.km is not None:
        m.km = body.km
    db.add(m)
    db.commit()
    db.refresh(m)
    if (
        body.status is not None
        and m.status == MotoStatus.MANUTENCAO.value
        and old_status != MotoStatus.MANUTENCAO.value
    ):
        from motopay.infrastructure.messaging.dispatch import enqueue_domain_event

        ev = EventoDominio(
            tipo=DomainEventType.MOTO_EM_MANUTENCAO.value,
            payload={"moto_id": m.id, "operacao_id": m.operacao_id},
        )
        db.add(ev)
        db.commit()
        db.refresh(ev)
        enqueue_domain_event(ev.id)
    return m


def delete_moto(
    db: Session, user: CurrentUser, operacao_scope: int | None, moto_id: int
) -> None:
    """Exclui um veículo e suas dependências.

    Regras de segurança por causa das FKs:
    - bloqueia (409) se houver contratos vinculados (Contrato.moto_id é não-nulo);
    - bloqueia (409) se houver multas vinculadas (Multa.moto_id é não-nulo);
    - desvincula lançamentos financeiros (preserva o histórico: moto_id = NULL);
    - remove a imagem do storage, se houver;
    - apaga o veículo.
    """
    m = get_moto(db, user, operacao_scope, moto_id)

    contratos = (
        db.scalar(select(func.count()).select_from(Contrato).where(Contrato.moto_id == m.id)) or 0
    )
    if contratos:
        raise ConflictError(
            "Não é possível excluir um veículo com contratos vinculados. "
            "Cancele ou encerre os contratos do veículo antes de excluí-lo."
        )
    multas = db.scalar(select(func.count()).select_from(Multa).where(Multa.moto_id == m.id)) or 0
    if multas:
        raise ConflictError(
            "Não é possível excluir um veículo com multas vinculadas. "
            "Exclua as multas do veículo antes de excluí-lo."
        )

    db.execute(update(Financeiro).where(Financeiro.moto_id == m.id).values(moto_id=None))

    from motopay.domain.enums import AnexoEntidade
    from motopay.services.anexo_service import delete_anexos_for_entity

    delete_anexos_for_entity(db, AnexoEntidade.MOTO.value, m.id, m.operacao_id, commit=False)

    old_image = m.imagem_path
    db.delete(m)
    db.commit()

    if old_image:
        from motopay.infrastructure.storage import get_storage

        try:
            get_storage().delete(old_image)
        except Exception:  # nunca deixa a limpeza de arquivo derrubar a exclusão
            logger.warning("Falha ao remover imagem do veículo %s na exclusão", moto_id, exc_info=True)


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
    clientes = list(db.scalars(base.order_by(Cliente.id).limit(limit).offset(offset)).unique().all())
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
        sobrenome=body.sobrenome.strip() if body.sobrenome else None,
        cpf=cpf,
        telefone=body.telefone.strip(),
        email=body.email.strip().lower() if body.email else None,
        telegram_id=body.telegram_id.strip() if body.telegram_id else None,
        endereco_logradouro=(body.endereco_logradouro or "").strip() or None,
        endereco_numero=(body.endereco_numero or "").strip() or None,
        endereco_bairro=(body.endereco_bairro or "").strip() or None,
        endereco_cidade=(body.endereco_cidade or "").strip() or None,
        endereco_estado=((body.endereco_estado or "").strip().upper() or None),
        endereco_cep=(body.endereco_cep or "").strip() or None,
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
    if body.sobrenome is not None:
        c.sobrenome = body.sobrenome.strip() if body.sobrenome else None
    if body.telefone is not None:
        c.telefone = body.telefone.strip()
    if body.email is not None:
        c.email = body.email.strip().lower() if body.email else None
    if body.telegram_id is not None:
        c.telegram_id = body.telegram_id.strip() if body.telegram_id else None
    if body.endereco_logradouro is not None:
        c.endereco_logradouro = body.endereco_logradouro.strip() or None
    if body.endereco_numero is not None:
        c.endereco_numero = body.endereco_numero.strip() or None
    if body.endereco_bairro is not None:
        c.endereco_bairro = body.endereco_bairro.strip() or None
    if body.endereco_cidade is not None:
        c.endereco_cidade = body.endereco_cidade.strip() or None
    if body.endereco_estado is not None:
        c.endereco_estado = body.endereco_estado.strip().upper() or None
    if body.endereco_cep is not None:
        c.endereco_cep = body.endereco_cep.strip() or None
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def delete_cliente(db: Session, user: CurrentUser, operacao_scope: int | None, cliente_id: int):
    c = get_cliente(db, user, operacao_scope, cliente_id)
    # Contrato.cliente_id é FK sem cascade: excluir um cliente com contratos
    # estoura IntegrityError (→ 500). Bloqueia com mensagem clara (409).
    contratos = (
        db.scalar(select(func.count()).select_from(Contrato).where(Contrato.cliente_id == c.id))
        or 0
    )
    if contratos:
        raise ConflictError(
            "Não é possível excluir um cliente com contratos vinculados. "
            "Cancele ou encerre os contratos do cliente antes de excluí-lo."
        )
    from motopay.domain.enums import AnexoEntidade
    from motopay.services.anexo_service import delete_anexos_for_entity

    delete_anexos_for_entity(db, AnexoEntidade.CLIENTE.value, c.id, c.operacao_id, commit=False)
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


def delete_contrato(
    db: Session, user: CurrentUser, operacao_scope: int | None, contrato_id: int
) -> None:
    """Exclui um contrato e suas dependências.

    Ordem segura por causa das FKs:
    - cancela a assinatura recorrente no MP (best-effort, não bloqueia);
    - apaga as cobranças do contrato (FK não-nula);
    - desvincula lançamentos financeiros (preserva o histórico: contrato_id = NULL);
    - libera a moto (alugada → disponível);
    - apaga o contrato.
    """
    ct = get_contrato(db, user, operacao_scope, contrato_id)

    if (ct.mercadopago_subscription_id or "").strip():
        try:
            from motopay.services.billing_service import (
                cancel_mercadopago_subscription_for_contract,
            )

            cancel_mercadopago_subscription_for_contract(db, ct)
        except Exception:  # cancelamento no MP nunca pode impedir a exclusão local
            logger.warning(
                "Falha ao cancelar assinatura MP do contrato %s na exclusão", ct.id, exc_info=True
            )

    db.execute(delete(Cobranca).where(Cobranca.contrato_id == ct.id))
    db.execute(
        update(Financeiro).where(Financeiro.contrato_id == ct.id).values(contrato_id=None)
    )

    moto = db.get(Moto, ct.moto_id)
    if moto and moto.status == MotoStatus.ALUGADA.value:
        moto.status = MotoStatus.DISPONIVEL.value
        db.add(moto)

    db.delete(ct)
    db.commit()


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
        raise NotFoundError("Veículo inválido para esta operação")
    max_numero = db.scalar(
        select(func.coalesce(func.max(Contrato.numero), 0)).where(
            Contrato.operacao_id == operacao_id
        )
    ) or 0
    ct = Contrato(
        operacao_id=operacao_id,
        numero=max_numero + 1,
        cliente_id=body.cliente_id,
        moto_id=body.moto_id,
        valor_recorrente=body.valor_recorrente,
        valor_caucao=body.valor_caucao,
        km_entrega=body.km_entrega,
        ciclo=body.ciclo.value,
        status=body.status.value,
        data_inicio=body.data_inicio,
        data_fim_vigencia=body.data_fim_vigencia,
        proximo_vencimento=body.proximo_vencimento,
    )
    db.add(ct)
    moto.status = MotoStatus.ALUGADA.value
    # Mantém o odômetro do veículo coerente com o km informado na entrega.
    if body.km_entrega is not None and body.km_entrega > moto.km:
        moto.km = body.km_entrega
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
    from motopay.domain.enums import ContratoStatus as CS
    from motopay.services.billing_service import (
        cancel_mercadopago_subscription_for_contract,
        sync_mercadopago_subscription_amount,
    )

    ct = get_contrato(db, user, operacao_scope, contrato_id)
    ending = (
        body.status is not None
        and body.status.value in (CS.FINALIZADO.value, CS.CANCELADO.value)
        and ct.status == CS.ATIVO.value
    )
    valor_changed = False
    ciclo_changed = False
    if body.status is not None:
        ct.status = body.status.value
    if body.valor_recorrente is not None:
        valor_changed = body.valor_recorrente != ct.valor_recorrente
        ct.valor_recorrente = body.valor_recorrente
    if body.valor_caucao is not None:
        ct.valor_caucao = body.valor_caucao
    if body.km_entrega is not None:
        ct.km_entrega = body.km_entrega
    if body.km_devolucao is not None:
        ct.km_devolucao = body.km_devolucao
    if body.ciclo is not None:
        ciclo_changed = body.ciclo.value != ct.ciclo
        ct.ciclo = body.ciclo.value
    if body.data_fim_vigencia is not None:
        if body.data_fim_vigencia < ct.data_inicio:
            raise ConflictError("data_fim_vigencia deve ser igual ou posterior a data_inicio")
        ct.data_fim_vigencia = body.data_fim_vigencia
    if body.proximo_vencimento is not None:
        if body.proximo_vencimento < ct.data_inicio:
            raise ConflictError("proximo_vencimento deve ser igual ou posterior a data_inicio")
        ct.proximo_vencimento = body.proximo_vencimento
    if ending:
        cancel_mercadopago_subscription_for_contract(db, ct)
        moto = db.get(Moto, ct.moto_id)
        if moto:
            moto.status = MotoStatus.DISPONIVEL.value
            # Atualiza o odômetro do veículo com o km informado na devolução.
            if ct.km_devolucao is not None and ct.km_devolucao > moto.km:
                moto.km = ct.km_devolucao
            db.add(moto)
    db.add(ct)
    db.commit()
    db.refresh(ct)
    if (valor_changed or ciclo_changed) and ct.mercadopago_subscription_id and not ending:
        sync_mercadopago_subscription_amount(db, ct)
    return ct
