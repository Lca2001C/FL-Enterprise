from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from motopay.infrastructure.db.session import get_db
from motopay.interfaces.api.deps import CurrentUser, require_dono_or_admin, resolve_operacao_id
from motopay.interfaces.api.schemas import CobrancaOut, CreateChargeRequest
from motopay.services.billing_service import (
    create_asaas_subscription_for_contract,
    create_pix_charge_for_contract,
    list_cobrancas,
)

router = APIRouter(prefix="/cobrancas", tags=["cobrancas"])


@router.get("", response_model=list[CobrancaOut])
def list_all(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_dono_or_admin),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> list[CobrancaOut]:
    return list_cobrancas(db, user, operacao_id)


@router.post("/pix", response_model=CobrancaOut)
def create_pix(
    body: CreateChargeRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_dono_or_admin),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> CobrancaOut:
    return create_pix_charge_for_contract(db, user, operacao_id, body.contrato_id)


@router.post("/assinatura-asaas", response_model=dict)
def create_subscription(
    body: CreateChargeRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_dono_or_admin),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> dict:
    ct = create_asaas_subscription_for_contract(db, user, operacao_id, body.contrato_id)
    return {"contrato_id": ct.id, "asaas_subscription_id": ct.asaas_subscription_id}
