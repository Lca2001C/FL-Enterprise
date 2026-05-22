from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from motopay.domain.exceptions import ForbiddenError, NotFoundError
from motopay.infrastructure.db.models import Operacao
from motopay.infrastructure.db.session import get_db
from motopay.interfaces.api.deps import CurrentUser, require_admin, require_dono_or_admin
from motopay.interfaces.api.schemas import OperacaoCreate, OperacaoOut, OperacaoUpdate
from motopay.services.operacao_service import (
    create_operacao,
    get_operacao_or_404,
    list_operacoes,
    update_operacao,
)

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
    if not user.operacao_id:
        raise ForbiddenError("Usuário sem operação vinculada")
    op = db.get(Operacao, user.operacao_id)
    if not op:
        raise NotFoundError("Operação não encontrada")
    return op


@router.patch("/me", response_model=OperacaoOut)
def update_my_op(
    body: OperacaoUpdate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_dono_or_admin),
) -> OperacaoOut:
    if not user.operacao_id:
        raise ForbiddenError("Usuário sem operação vinculada")
    return update_operacao(db, user.operacao_id, body)


@router.get("/{operacao_id:int}", response_model=OperacaoOut)
def get_op_by_id_admin(
    operacao_id: int,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
) -> OperacaoOut:
    op = get_operacao_or_404(db, operacao_id)
    if not op:
        raise NotFoundError("Operação não encontrada")
    return op


@router.patch("/{operacao_id:int}", response_model=OperacaoOut)
def update_op_by_id_admin(
    operacao_id: int,
    body: OperacaoUpdate,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
) -> OperacaoOut:
    if not get_operacao_or_404(db, operacao_id):
        raise NotFoundError("Operação não encontrada")
    return update_operacao(db, operacao_id, body)
