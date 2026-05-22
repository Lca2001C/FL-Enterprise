from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from motopay.infrastructure.db.session import get_db
from motopay.interfaces.api.deps import CurrentUser, require_dono_or_admin, resolve_operacao_id
from motopay.interfaces.api.schemas import MotoCreate, MotoOut, MotoUpdate
from motopay.services.fleet_service import (
    create_moto,
    get_moto,
    update_moto,
)
from motopay.services.fleet_service import (
    list_motos as list_motos_service,
)

router = APIRouter(prefix="/motos", tags=["motos"])


@router.get("", response_model=list[MotoOut])
def list_motos(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_dono_or_admin),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> list[MotoOut]:
    return list_motos_service(db, user, operacao_id)


@router.post("", response_model=MotoOut)
def create(
    body: MotoCreate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_dono_or_admin),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> MotoOut:
    return create_moto(db, user, operacao_id, body)


@router.get("/{moto_id}", response_model=MotoOut)
def get_one(
    moto_id: int,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_dono_or_admin),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> MotoOut:
    return get_moto(db, user, operacao_id, moto_id)


@router.patch("/{moto_id}", response_model=MotoOut)
def patch(
    moto_id: int,
    body: MotoUpdate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_dono_or_admin),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> MotoOut:
    return update_moto(db, user, operacao_id, moto_id, body)
