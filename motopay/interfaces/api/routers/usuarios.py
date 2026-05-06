from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from motopay.infrastructure.db.session import get_db
from motopay.interfaces.api.deps import CurrentUser, require_admin
from motopay.domain.enums import UserRole
from motopay.interfaces.api.schemas import UserOut, UsuarioCreate
from motopay.services.operacao_service import create_usuario_admin

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


@router.post("", response_model=UserOut)
def register_user(
    body: UsuarioCreate,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
) -> UserOut:
    u = create_usuario_admin(db, body)
    return UserOut(id=u.id, email=u.email, tipo=UserRole(u.tipo), operacao_id=u.operacao_id)
