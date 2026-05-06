from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from motopay.infrastructure.db.session import get_db
from motopay.interfaces.api.deps import CurrentUser, require_admin
from motopay.interfaces.api.schemas import OperacaoCreate, OperacaoOut
from motopay.services.operacao_service import create_operacao, list_operacoes

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
