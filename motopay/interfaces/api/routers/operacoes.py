from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from motopay.infrastructure.db.session import get_db
from motopay.interfaces.api.deps import CurrentUser, require_admin, require_dono_or_admin
from motopay.interfaces.api.schemas import OperacaoCreate, OperacaoOut, OperacaoUpdate
from motopay.services.operacao_service import create_operacao, list_operacoes, update_operacao

router = APIRouter(prefix="/operacoes", tags=["operacoes"])


@router.get("", response_model=list[OperacaoOut])
def list_ops(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_admin),
) -> list[OperacaoOut]:
    return list_operacoes(db, user)


@router.post("", response_model=OperacaoOut)
def create_op(
    body: OperacaoCreate,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
) -> OperacaoOut:
    return create_operacao(db, body)


@router.get("/me", response_model=OperacaoOut)
def get_my_op(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_dono_or_admin),
) -> OperacaoOut:
    from motopay.domain.exceptions import ForbiddenError
    if not user.operacao_id:
        raise ForbiddenError("Usuário sem operação vinculada")
    return db.get(Operacao, user.operacao_id)


@router.patch("/me", response_model=OperacaoOut)
def update_my_op(
    body: OperacaoUpdate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_dono_or_admin),
) -> OperacaoOut:
    from motopay.domain.exceptions import ForbiddenError, NotFoundError
    from motopay.infrastructure.db.models import Operacao
    if not user.operacao_id:
        raise ForbiddenError("Usuário sem operação vinculada")
    return update_operacao(db, user.operacao_id, body)
