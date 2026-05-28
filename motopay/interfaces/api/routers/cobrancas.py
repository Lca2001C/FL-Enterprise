from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from motopay.domain.enums import CobrancaStatus
from motopay.infrastructure.db.session import get_db
from motopay.interfaces.api.deps import CurrentUser, require_operacional, resolve_operacao_id
from motopay.interfaces.api.pagination import clamp_limit, clamp_offset
from motopay.interfaces.api.schemas import CobrancaOut, CreateChargeRequest, Paginated
from motopay.services.billing_service import (
    create_mercadopago_subscription_for_contract,
    create_pix_charge_for_contract,
    list_cobrancas,
)

router = APIRouter(prefix="/cobrancas", tags=["cobrancas"])


@router.get("", response_model=Paginated[CobrancaOut])
def list_all(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_operacional),
    operacao_id: int | None = Depends(resolve_operacao_id),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
    status: CobrancaStatus | None = Query(default=None),
) -> Paginated[CobrancaOut]:
    lim = clamp_limit(limit)
    off = clamp_offset(offset)
    rows, total = list_cobrancas(db, user, operacao_id, limit=lim, offset=off, status=status)
    return Paginated(items=rows, total=total, limit=lim, offset=off)


@router.post("/pix", response_model=CobrancaOut)
def create_pix(
    body: CreateChargeRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_operacional),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> CobrancaOut:
    return create_pix_charge_for_contract(db, user, operacao_id, body.contrato_id)


@router.post("/assinatura-mercadopago", response_model=dict)
def create_subscription(
    body: CreateChargeRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_operacional),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> dict:
    ct = create_mercadopago_subscription_for_contract(db, user, operacao_id, body.contrato_id)
    return {"contrato_id": ct.id, "mercadopago_subscription_id": ct.mercadopago_subscription_id}
