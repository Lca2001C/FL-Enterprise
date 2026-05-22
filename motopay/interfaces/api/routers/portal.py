from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from motopay.domain.exceptions import NotFoundError
from motopay.infrastructure.db.session import get_db
from motopay.interfaces.api.deps import CurrentUser, require_cliente
from motopay.interfaces.api.pagination import clamp_limit, clamp_offset
from motopay.interfaces.api.schemas import CobrancaOut, ContratoOut, Paginated
from motopay.services.billing_service import (
    get_active_contrato_for_cliente,
    list_cobrancas_for_cliente,
)

router = APIRouter(prefix="/portal", tags=["portal"])


@router.get("/contrato", response_model=ContratoOut)
def my_contrato(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_cliente),
) -> ContratoOut:
    ct = get_active_contrato_for_cliente(db, user.cliente_id)  # type: ignore[arg-type]
    if not ct:
        raise NotFoundError("Nenhum contrato ativo")
    return ct


@router.get("/cobrancas", response_model=Paginated[CobrancaOut])
def my_cobrancas(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_cliente),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> Paginated[CobrancaOut]:
    lim = clamp_limit(limit)
    off = clamp_offset(offset)
    rows, total = list_cobrancas_for_cliente(
        db, cliente_id=user.cliente_id, limit=lim, offset=off  # type: ignore[arg-type]
    )
    return Paginated(items=rows, total=total, limit=lim, offset=off)
