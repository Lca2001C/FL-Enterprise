from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

from motopay.domain.enums import CobrancaStatus
from motopay.infrastructure.db.models import Cobranca, EventoDominio, Operacao
from motopay.services.mercadopago_token_service import ensure_valid_mp_token


def test_ensure_valid_mp_token_refreshes_when_expired(db_session):
    op = Operacao(
        nome="OAuth Op",
        mercadopago_access_token="old-token",
        mercadopago_public_key="pk",
        mercadopago_webhook_secret="sec",
        mercadopago_refresh_token="refresh-xyz",
        mercadopago_oauth_expires_at=datetime.now(UTC) - timedelta(minutes=1),
    )
    db_session.add(op)
    db_session.commit()

    with patch(
        "motopay.services.mercadopago_token_service.refresh_oauth_token",
        return_value={
            "access_token": "new-token",
            "refresh_token": "refresh-new",
            "expires_in": 3600,
            "public_key": "pk-new",
        },
    ):
        token = ensure_valid_mp_token(db_session, op)

    assert token == "new-token"
    db_session.refresh(op)
    assert op.mercadopago_access_token == "new-token"
    assert op.mercadopago_refresh_token == "refresh-new"


def test_refund_emits_domain_event(db_session):
    from motopay.services.billing_service import handle_mercadopago_refund_confirmed

    op = Operacao(nome="Ev Op")
    db_session.add(op)
    db_session.flush()
    cob = Cobranca(
        operacao_id=op.id,
        contrato_id=1,
        valor=Decimal("100"),
        vencimento=datetime.now(UTC).date(),
        mercadopago_payment_id="pay-ev-1",
        status=CobrancaStatus.RECEBIDO.value,
    )
    db_session.add(cob)
    db_session.commit()

    ok, ev_id = handle_mercadopago_refund_confirmed(
        db_session,
        mercadopago_payment_id="pay-ev-1",
        refund_amount=Decimal("25"),
    )
    assert ok
    assert ev_id is not None
    ev = db_session.get(EventoDominio, ev_id)
    assert ev is not None
    assert ev.tipo == "ESTORNO_CONFIRMADO"
