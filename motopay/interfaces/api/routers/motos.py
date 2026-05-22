from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from motopay.domain.enums import MotoStatus
from motopay.infrastructure.db.session import get_db
from motopay.interfaces.api.deps import CurrentUser, require_operacional, resolve_operacao_id
from motopay.interfaces.api.pagination import clamp_limit, clamp_offset
from motopay.interfaces.api.schemas import MotoCreate, MotoOut, MotoUpdate, Paginated
from motopay.services.fleet_service import (
    create_moto,
    get_moto,
    update_moto,
)
from motopay.services.fleet_service import (
    list_motos as list_motos_service,
)

router = APIRouter(prefix="/motos", tags=["motos"])


@router.get("", response_model=Paginated[MotoOut])
def list_motos(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_operacional),
    operacao_id: int | None = Depends(resolve_operacao_id),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
    status: MotoStatus | None = Query(default=None),
    q: str | None = Query(default=None),
) -> Paginated[MotoOut]:
    lim = clamp_limit(limit)
    off = clamp_offset(offset)
    rows, total = list_motos_service(
        db, user, operacao_id, limit=lim, offset=off, status=status, q=q
    )
    return Paginated(items=rows, total=total, limit=lim, offset=off)


@router.post("", response_model=MotoOut)
def create(
    body: MotoCreate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_operacional),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> MotoOut:
    return create_moto(db, user, operacao_id, body)


@router.get("/{moto_id}", response_model=MotoOut)
def get_one(
    moto_id: int,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_operacional),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> MotoOut:
    return get_moto(db, user, operacao_id, moto_id)


@router.patch("/{moto_id}", response_model=MotoOut)
def patch(
    moto_id: int,
    body: MotoUpdate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_operacional),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> MotoOut:
    return update_moto(db, user, operacao_id, moto_id, body)
