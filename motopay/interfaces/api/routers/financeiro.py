from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from motopay.infrastructure.db.session import get_db
from motopay.interfaces.api.deps import CurrentUser, require_dono_or_admin, resolve_operacao_id
from motopay.interfaces.api.schemas import FinanceiroCreate, FinanceiroOut
from motopay.services.finance_service import (
    create_financeiro,
    list_financeiro as list_financeiro_service,
)

router = APIRouter(prefix="/financeiro", tags=["financeiro"])


@router.get("", response_model=list[FinanceiroOut])
def list_rows(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_dono_or_admin),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> list[FinanceiroOut]:
    return list_financeiro_service(db, user, operacao_id)


@router.post("", response_model=FinanceiroOut)
def create(
    body: FinanceiroCreate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_dono_or_admin),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> FinanceiroOut:
    return create_financeiro(db, user, operacao_id, body)
