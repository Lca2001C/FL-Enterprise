from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from motopay.infrastructure.db.session import get_db
from motopay.interfaces.api.schemas import (
    CardPaymentOut,
    ClienteMpCardOut,
    CobrancaOut,
    PayerPortalOut,
    PortalCardPaymentRequest,
)
from motopay.services.payer_portal_service import (
    get_portal_checkout,
    list_portal_saved_cards,
    portal_generate_pix,
    portal_pay_card,
)

router = APIRouter(prefix="/public/pay", tags=["public-pay"])


@router.get("/{token}", response_model=PayerPortalOut)
def public_checkout(token: str, db: Session = Depends(get_db)) -> PayerPortalOut:
    return get_portal_checkout(db, token)


@router.get("/{token}/cards", response_model=list[ClienteMpCardOut])
def public_cards(token: str, db: Session = Depends(get_db)) -> list[ClienteMpCardOut]:
    return list_portal_saved_cards(db, token)


@router.post("/{token}/pix", response_model=CobrancaOut)
def public_pix(token: str, db: Session = Depends(get_db)) -> CobrancaOut:
    return portal_generate_pix(db, token)


@router.post("/{token}/card", response_model=CardPaymentOut)
def public_card(
    token: str,
    body: PortalCardPaymentRequest,
    db: Session = Depends(get_db),
) -> CardPaymentOut:
    kind = (
        body.payment_method_kind
        if body.payment_method_kind in ("credit_card", "debit_card")
        else "credit_card"
    )
    return portal_pay_card(
        db,
        token,
        card_token=body.token,
        payment_method_id=body.payment_method_id,
        payment_method_kind=kind,
        installments=body.installments,
        saved_card_id=body.saved_card_id,
    )
