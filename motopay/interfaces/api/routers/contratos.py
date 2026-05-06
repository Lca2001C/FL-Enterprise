from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from motopay.infrastructure.db.session import get_db
from motopay.interfaces.api.deps import CurrentUser, require_dono_or_admin, resolve_operacao_id
from motopay.interfaces.api.schemas import ContratoCreate, ContratoOut, ContratoUpdate
from motopay.services.fleet_service import (
    create_contrato,
    get_contrato,
    list_contratos as list_contratos_service,
    update_contrato,
)

router = APIRouter(prefix="/contratos", tags=["contratos"])


@router.get("", response_model=list[ContratoOut])
def list_contratos(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_dono_or_admin),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> list[ContratoOut]:
    return list_contratos_service(db, user, operacao_id)


@router.post("", response_model=ContratoOut)
def create(
    body: ContratoCreate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_dono_or_admin),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> ContratoOut:
    return create_contrato(db, user, operacao_id, body)


@router.get("/{contrato_id}", response_model=ContratoOut)
def get_one(
    contrato_id: int,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_dono_or_admin),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> ContratoOut:
    return get_contrato(db, user, operacao_id, contrato_id)


@router.patch("/{contrato_id}", response_model=ContratoOut)
def patch(
    contrato_id: int,
    body: ContratoUpdate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_dono_or_admin),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> ContratoOut:
    return update_contrato(db, user, operacao_id, contrato_id, body)
