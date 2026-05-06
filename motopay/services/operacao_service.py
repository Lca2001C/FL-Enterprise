from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from motopay.domain.enums import UserRole
from motopay.domain.exceptions import ConflictError, ForbiddenError
from motopay.infrastructure.db.models import Operacao, Usuario
from motopay.interfaces.api.deps import CurrentUser
from motopay.interfaces.api.schemas import OperacaoCreate, UsuarioCreate
from motopay.services.auth_service import hash_password


def create_operacao(db: Session, body: OperacaoCreate) -> Operacao:
    op = Operacao(nome=body.nome.strip())
    db.add(op)
    db.commit()
    db.refresh(op)
    return op


def create_usuario_admin(db: Session, body: UsuarioCreate) -> Usuario:
    if db.scalars(select(Usuario).where(Usuario.email == str(body.email))).first():
        raise ConflictError("E-mail já cadastrado")
    if body.tipo == UserRole.DONO and body.operacao_id is None:
        raise ConflictError("Dono exige operacao_id")
    if body.tipo == UserRole.ADMIN and body.operacao_id is not None:
        raise ConflictError("Admin não deve ter operacao_id")
    if body.operacao_id is not None:
        parent = db.get(Operacao, body.operacao_id)
        if not parent:
            raise ConflictError("Operação inexistente")
    user = Usuario(
        email=str(body.email).lower(),
        senha_hash=hash_password(body.password),
        tipo=body.tipo.value,
        operacao_id=body.operacao_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_operacao_or_404(db: Session, operacao_id: int) -> Operacao | None:
    return db.get(Operacao, operacao_id)


def list_operacoes(db: Session, user: CurrentUser) -> list[Operacao]:
    if user.role != UserRole.ADMIN:
        raise ForbiddenError("Somente admin")
    return list(db.scalars(select(Operacao).order_by(Operacao.id)).all())
