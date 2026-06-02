from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from motopay.domain.enums import CobrancaStatus
from motopay.infrastructure.db.session import get_db
from motopay.interfaces.api.deps import CurrentUser, require_operacional, resolve_operacao_id
from motopay.interfaces.api.pagination import clamp_limit, clamp_offset
from motopay.interfaces.api.schemas import (
    CardPaymentOut,
    CardPaymentRequest,
    CobrancaOut,
    CreateChargeRequest,
    Paginated,
)
from motopay.services.billing_service import (
    create_mercadopago_subscription_for_contract,
    create_pix_charge_for_contract,
    ensure_pix_for_cobranca,
    list_cobrancas,
)
from motopay.services.card_payment_service import pay_cobranca_with_card

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


@router.post("/{cobranca_id}/pix", response_model=CobrancaOut)
def ensure_pix(
    cobranca_id: int,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_operacional),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> CobrancaOut:
    return ensure_pix_for_cobranca(db, user, operacao_id, cobranca_id)


@router.post("/{cobranca_id}/card-payment", response_model=CardPaymentOut)
def pay_with_card(
    cobranca_id: int,
    body: CardPaymentRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_operacional),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> CardPaymentOut:
    from motopay.infrastructure.messaging.tasks import handle_domain_event

    out = pay_cobranca_with_card(
        db,
        user,
        operacao_id,
        cobranca_id,
        token=body.token,
        saved_card_id=body.saved_card_id,
        installments=body.installments,
        payment_method_id=body.payment_method_id,
        payment_method_kind=body.payment_method_kind,
    )
    if out.domain_event_id:
        handle_domain_event.delay(out.domain_event_id)
    return out


@router.post("/assinatura-mercadopago", response_model=dict)
def create_subscription(
    body: CreateChargeRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_operacional),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> dict:
    ct = create_mercadopago_subscription_for_contract(db, user, operacao_id, body.contrato_id)
    return {"contrato_id": ct.id, "mercadopago_subscription_id": ct.mercadopago_subscription_id}
