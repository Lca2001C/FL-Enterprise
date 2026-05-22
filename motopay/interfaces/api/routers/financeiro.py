from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from motopay.infrastructure.db.session import get_db
from motopay.interfaces.api.deps import CurrentUser, require_operacional, resolve_operacao_id
from motopay.interfaces.api.pagination import clamp_limit, clamp_offset
from motopay.interfaces.api.schemas import FinanceiroCreate, FinanceiroOut, Paginated
from motopay.services.finance_service import (
    create_financeiro,
)
from motopay.services.finance_service import (
    list_financeiro as list_financeiro_service,
)

router = APIRouter(prefix="/financeiro", tags=["financeiro"])


@router.get("", response_model=Paginated[FinanceiroOut])
def list_rows(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_operacional),
    operacao_id: int | None = Depends(resolve_operacao_id),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> Paginated[FinanceiroOut]:
    lim = clamp_limit(limit)
    off = clamp_offset(offset)
    rows, total = list_financeiro_service(db, user, operacao_id, limit=lim, offset=off)
    return Paginated(items=rows, total=total, limit=lim, offset=off)


@router.post("", response_model=FinanceiroOut)
def create(
    body: FinanceiroCreate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_operacional),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> FinanceiroOut:
    return create_financeiro(db, user, operacao_id, body)
