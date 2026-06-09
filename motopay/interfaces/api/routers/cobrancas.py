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
    MpSubscriptionOut,
    Paginated,
    PortalLinkOut,
    RefundRequest,
)
from motopay.services.billing_service import (
    create_mercadopago_subscription_for_contract,
    create_pix_charge_for_contract,
    ensure_pix_for_cobranca,
    get_cobranca,
    list_cobrancas,
    refund_cobranca_mercadopago,
)
from motopay.services.card_payment_service import pay_cobranca_with_card
from motopay.services.payer_portal_service import issue_portal_link, revoke_portal_link

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


@router.get("/{cobranca_id}", response_model=CobrancaOut)
def get_one(
    cobranca_id: int,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_operacional),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> CobrancaOut:
    return get_cobranca(db, user, operacao_id, cobranca_id)


@router.post("/pix", response_model=CobrancaOut)
def create_pix(
    body: CreateChargeRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_operacional),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> CobrancaOut:
    return create_pix_charge_for_contract(
        db, user, operacao_id, body.contrato_id, device_id=body.device_id
    )


@router.post("/{cobranca_id}/pix", response_model=CobrancaOut)
def generate_pix_for_cobranca(
    cobranca_id: int,
    device_id: str | None = Query(default=None, description="MP_DEVICE_SESSION_ID do frontend"),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_operacional),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> CobrancaOut:
    return ensure_pix_for_cobranca(db, user, operacao_id, cobranca_id, device_id=device_id)


@router.post("/{cobranca_id}/card", response_model=CardPaymentOut)
def pay_with_card(
    cobranca_id: int,
    body: CardPaymentRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_operacional),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> CardPaymentOut:
    kind = body.payment_method_kind if body.payment_method_kind in ("credit_card", "debit_card") else "credit_card"
    return pay_cobranca_with_card(
        db,
        user,
        operacao_id,
        cobranca_id=cobranca_id,
        token=body.token,
        payment_method_id=body.payment_method_id,
        payment_method_kind=kind,  # type: ignore[arg-type]
        saved_card_id=body.saved_card_id,
        installments=body.installments,
        device_id=body.device_id,
    )


@router.post("/{cobranca_id}/portal-link", response_model=PortalLinkOut)
def create_portal_link(
    cobranca_id: int,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_operacional),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> PortalLinkOut:
    data = issue_portal_link(db, user, operacao_id, cobranca_id)
    return PortalLinkOut.model_validate(data)


@router.delete("/{cobranca_id}/portal-link")
def delete_portal_link(
    cobranca_id: int,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_operacional),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> dict[str, bool]:
    revoke_portal_link(db, user, operacao_id, cobranca_id)
    return {"ok": True}


@router.post("/{cobranca_id}/refund", response_model=CobrancaOut)
def refund_cobranca(
    cobranca_id: int,
    body: RefundRequest | None = None,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_operacional),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> CobrancaOut:
    amount = body.amount if body else None
    return refund_cobranca_mercadopago(
        db, user, operacao_id, cobranca_id, amount=amount
    )


@router.post("/assinatura-mercadopago", response_model=MpSubscriptionOut)
def create_subscription(
    body: CreateChargeRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_operacional),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> MpSubscriptionOut:
    data = create_mercadopago_subscription_for_contract(db, user, operacao_id, body.contrato_id)
    return MpSubscriptionOut.model_validate(data)
