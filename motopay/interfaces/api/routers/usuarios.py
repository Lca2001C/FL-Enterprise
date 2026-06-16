from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from motopay.domain.enums import UserRole
from motopay.domain.exceptions import ForbiddenError
from motopay.infrastructure.db.session import get_db
from motopay.interfaces.api.deps import (
    CurrentUser,
    require_admin,
    require_settings_access,
    resolve_operacao_id,
)
from motopay.interfaces.api.pagination import clamp_limit, clamp_offset
from motopay.interfaces.api.schemas import (
    OperacaoUsuarioCreate,
    Paginated,
    UserAdminOut,
    UserOut,
    UsuarioCreate,
)
from motopay.services.operacao_service import (
    create_operacao_usuario,
    create_usuario_admin,
    list_usuarios_admin,
)

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


@router.get("", response_model=Paginated[UserAdminOut])
def list_users(
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
    tipo: UserRole | None = Query(default=None),
    operacao_id: int | None = Query(default=None),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> Paginated[UserAdminOut]:
    lim = clamp_limit(limit)
    off = clamp_offset(offset)
    rows, total = list_usuarios_admin(
        db,
        tipo=tipo,
        operacao_id=operacao_id,
        limit=lim,
        offset=off,
    )
    return Paginated(items=rows, total=total, limit=lim, offset=off)


@router.post("", response_model=UserOut)
def register_user(
    body: UsuarioCreate,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
) -> UserOut:
    u = create_usuario_admin(db, body)
    return UserOut(
        id=u.id,
        email=u.email,
        tipo=UserRole(u.tipo),
        operacao_id=u.operacao_id,
    )


@router.get("/equipe", response_model=Paginated[UserAdminOut])
def list_equipe(
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_settings_access),
    operacao_id: int | None = Depends(resolve_operacao_id),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> Paginated[UserAdminOut]:
    """Usuários da própria operação. DONO: sempre a do token; ADMIN: via operacao_id/header."""
    if operacao_id is None:
        raise ForbiddenError("Informe a operação (operacao_id)")
    lim = clamp_limit(limit)
    off = clamp_offset(offset)
    rows, total = list_usuarios_admin(db, operacao_id=operacao_id, limit=lim, offset=off)
    return Paginated(items=rows, total=total, limit=lim, offset=off)


@router.post("/equipe", response_model=UserOut)
def add_equipe_user(
    body: OperacaoUsuarioCreate,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_settings_access),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> UserOut:
    """Adiciona um usuário (co-DONO) à própria operação. DONO não pode escolher
    outra operação: resolve_operacao_id força a operação do token."""
    u = create_operacao_usuario(db, operacao_id, body)
    return UserOut(
        id=u.id,
        email=u.email,
        tipo=UserRole(u.tipo),
        operacao_id=u.operacao_id,
    )
