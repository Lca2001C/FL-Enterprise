from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from motopay.config import get_settings
from motopay.config.mercadopago_credentials import effective_mercadopago_credentials_mode
from motopay.infrastructure.db.models import Operacao
from motopay.infrastructure.db.session import get_db
from motopay.infrastructure.payments.mercadopago_client import (
    mp_configured_for_operacao,
    mp_credentials_complete,
    mp_credentials_source,
    mp_has_operacao_token,
    mp_public_key_for_operacao,
    mp_webhook_secret_for_operacao,
)
from motopay.interfaces.api.deps import CurrentUser, require_operacional, resolve_operacao_id
from motopay.interfaces.api.schemas import PaymentsConfigOut

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/payments", response_model=PaymentsConfigOut)
def payments_config(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_operacional),
    operacao_id: int | None = Depends(resolve_operacao_id),
) -> PaymentsConfigOut:
    op: Operacao | None = None
    if operacao_id is not None:
        op = db.get(Operacao, operacao_id)
    elif user.operacao_id is not None:
        op = db.get(Operacao, user.operacao_id)

    mode = effective_mercadopago_credentials_mode()
    public_key = mp_public_key_for_operacao(op)
    webhook_secret = mp_webhook_secret_for_operacao(op)
    base = get_settings().api_public_base_url.rstrip("/")
    settings = get_settings()
    oauth_available = bool(settings.mercadopago_oauth_client_id.strip())
    oauth_connected = bool(
        op
        and (
            op.mercadopago_oauth_user_id
            or op.mercadopago_refresh_token
        )
    )
    webhook_ready = bool(webhook_secret)
    return PaymentsConfigOut(
        mercadopago_configured=mp_configured_for_operacao(op),
        mercadopago_public_key=public_key or None,
        webhook_configured=bool(webhook_secret),
        credentials_mode=mode,
        mercadopago_credentials_source=mp_credentials_source(op),
        mercadopago_credentials_complete=mp_credentials_complete(op),
        mercadopago_has_operacao_token=mp_has_operacao_token(op),
        mercadopago_oauth_available=oauth_available,
        mercadopago_oauth_connected=oauth_connected,
        mercadopago_webhook_ready=webhook_ready,
        webhook_url=f"{base}/webhooks/mercadopago",
    )
