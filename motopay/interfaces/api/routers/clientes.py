from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from motopay.infrastructure.db.session import get_db
from motopay.interfaces.api.deps import CurrentUser, require_dono_or_admin, resolve_operacao_id
from motopay.interfaces.api.schemas import ClienteCreate, ClienteOut, ClienteUpdate
from motopay.services.fleet_service import (
    create_cliente,
    get_cliente,
    list_clientes as list_clientes_service,
    update_cliente,
)

router = APIRouter(prefix="/clientes", tags=["clientes"])


@router.get("", response_model=list[ClienteOut])
def list_clientes(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_dono_or_admin),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> list[ClienteOut]:
    return list_clientes_service(db, user, operacao_id)


@router.post("", response_model=ClienteOut)
def create(
    body: ClienteCreate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_dono_or_admin),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> ClienteOut:
    return create_cliente(db, user, operacao_id, body)


@router.get("/{cliente_id}", response_model=ClienteOut)
def get_one(
    cliente_id: int,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_dono_or_admin),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> ClienteOut:
    return get_cliente(db, user, operacao_id, cliente_id)


@router.patch("/{cliente_id}", response_model=ClienteOut)
def patch(
    cliente_id: int,
    body: ClienteUpdate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_dono_or_admin),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> ClienteOut:
    return update_cliente(db, user, operacao_id, cliente_id, body)
