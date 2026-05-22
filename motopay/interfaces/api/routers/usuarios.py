from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from motopay.domain.enums import UserRole
from motopay.infrastructure.db.session import get_db
from motopay.interfaces.api.deps import CurrentUser, require_admin
from motopay.interfaces.api.pagination import clamp_limit, clamp_offset
from motopay.interfaces.api.schemas import Paginated, UserAdminOut, UserOut, UsuarioCreate
from motopay.services.operacao_service import create_usuario_admin, list_usuarios_admin

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
        cliente_id=u.cliente_id,
    )
