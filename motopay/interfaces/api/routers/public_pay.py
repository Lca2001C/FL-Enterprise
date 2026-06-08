from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from motopay.infrastructure.db.session import get_db
from motopay.infrastructure.security.client_ip import get_client_ip
from motopay.infrastructure.security.rate_limit import assert_portal_not_blocked, record_portal_failure
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


def _check_portal_rate(request: Request) -> None:
    ip = get_client_ip(request)
    assert_portal_not_blocked(ip)


@router.get("/{token}", response_model=PayerPortalOut)
def public_checkout(token: str, request: Request, db: Session = Depends(get_db)) -> PayerPortalOut:
    _check_portal_rate(request)
    try:
        return get_portal_checkout(db, token)
    except Exception:
        record_portal_failure(get_client_ip(request))
        raise


@router.get("/{token}/cards", response_model=list[ClienteMpCardOut])
def public_cards(token: str, request: Request, db: Session = Depends(get_db)) -> list[ClienteMpCardOut]:
    _check_portal_rate(request)
    return list_portal_saved_cards(db, token)


@router.post("/{token}/pix", response_model=CobrancaOut)
def public_pix(token: str, request: Request, db: Session = Depends(get_db)) -> CobrancaOut:
    _check_portal_rate(request)
    return portal_generate_pix(db, token)


@router.post("/{token}/card", response_model=CardPaymentOut)
def public_card(
    token: str,
    body: PortalCardPaymentRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> CardPaymentOut:
    _check_portal_rate(request)
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
