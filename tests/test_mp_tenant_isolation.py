"""Isolamento multi-tenant Mercado Pago: cada operação usa seu próprio token OAuth."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest

from motopay.config import get_settings
from motopay.domain.exceptions import MercadoPagoNotConnectedError
from motopay.infrastructure.crypto.token_encryption import encrypt_token
from motopay.infrastructure.db.models import Cliente, Operacao
from motopay.infrastructure.payments.mercadopago_client import (
    MP_NOT_CONNECTED_MSG,
    MercadoPagoApiError,
    require_operacao_mp_token,
)
from motopay.infrastructure.payments.order_utils import MercadoPagoOrderResult, ThreeDsInfo
from motopay.services.mercadopago_token_service import ensure_valid_mp_token
from motopay.services.payment_gateway import create_pix_for_cobranca

_TOKEN_A = "APP_USR-aaaaaaaaaaaaaaaa-tenant-a"
_TOKEN_B = "APP_USR-bbbbbbbbbbbbbbbb-tenant-b"
_PUBLIC_KEY = "APP_USR-pk-1234-5678-oauth"


def _wire_operacao_mp(
    op: Operacao,
    *,
    access_token: str,
    oauth_user_id: str,
) -> None:
    op.mercadopago_access_token = encrypt_token(access_token)
    op.mercadopago_public_key = _PUBLIC_KEY
    op.mercadopago_refresh_token = encrypt_token(f"refresh-{oauth_user_id}")
    op.mercadopago_oauth_user_id = oauth_user_id
    op.mercadopago_oauth_expires_at = datetime.now(UTC) + timedelta(days=30)
    op.mercadopago_connection_status = "connected"


@pytest.fixture
def mp_tenant_ops(db_session):
    op_a = Operacao(nome="Tenant A")
    op_b = Operacao(nome="Tenant B")
    _wire_operacao_mp(op_a, access_token=_TOKEN_A, oauth_user_id="111")
    _wire_operacao_mp(op_b, access_token=_TOKEN_B, oauth_user_id="222")
    db_session.add_all([op_a, op_b])
    db_session.flush()
    return op_a, op_b


def test_require_operacao_mp_token_uses_tenant_token(db_session, mp_tenant_ops):
    op_a, op_b = mp_tenant_ops
    assert require_operacao_mp_token(db_session, op_a) == _TOKEN_A
    assert require_operacao_mp_token(db_session, op_b) == _TOKEN_B


def test_create_pix_uses_correct_tenant_token(db_session, mp_tenant_ops):
    op_a, op_b = mp_tenant_ops
    captured: list[str] = []

    class FakeClient:
        def __init__(self, *, access_token: str | None = None) -> None:
            captured.append(access_token or "")

        def create_online_order(self, **kwargs):
            return MercadoPagoOrderResult(
                order_id="ord-1",
                payment_id="pay-1",
                order_status="pending",
                payment_status="pending",
                status_detail="",
                pix_copia_cola="pix-code",
                three_ds_info=ThreeDsInfo(None, None),
                requires_3ds=False,
            )

    cliente = Cliente(
        operacao_id=op_a.id,
        nome="Cliente",
        cpf="12345678901",
        telefone="11999999999",
        email="a@test.local",
    )
    db_session.add(cliente)
    db_session.flush()
    cliente_b = Cliente(
        operacao_id=op_b.id,
        nome="Cliente B",
        cpf="98765432100",
        telefone="11888888888",
        email="b@test.local",
    )
    db_session.add(cliente_b)
    db_session.flush()

    with patch(
        "motopay.services.payment_gateway.MercadoPagoClient",
        FakeClient,
    ):
        create_pix_for_cobranca(
            op=op_a,
            cliente=cliente,
            cobranca_id=99,
            valor_total=Decimal("50"),
            due_date=datetime.now(UTC).date(),
            db=db_session,
        )
        create_pix_for_cobranca(
            op=op_b,
            cliente=cliente_b,
            cobranca_id=100,
            valor_total=Decimal("75"),
            due_date=datetime.now(UTC).date(),
            db=db_session,
        )

    assert captured == [_TOKEN_A, _TOKEN_B]
    assert _TOKEN_A not in captured[1:]
    assert _TOKEN_B not in captured[:1]


def test_production_rejects_without_oauth(db_session, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    get_settings.cache_clear()
    op = Operacao(nome="Sem OAuth")
    db_session.add(op)
    db_session.flush()
    with pytest.raises(MercadoPagoNotConnectedError, match=MP_NOT_CONNECTED_MSG):
        require_operacao_mp_token(db_session, op)
    get_settings.cache_clear()


def test_global_token_not_used_for_tenant_in_production(db_session, monkeypatch, mp_tenant_ops):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("MERCADOPAGO_ACCESS_TOKEN", "APP_USR-global-dev-should-not-use")
    monkeypatch.setenv("MERCADOPAGO_WEBHOOK_SECRET", "whsec-prod-webhook-secret-1")
    get_settings.cache_clear()
    op_a, _ = mp_tenant_ops
    token = require_operacao_mp_token(db_session, op_a)
    assert token == _TOKEN_A
    assert "global-dev" not in token
    get_settings.cache_clear()


def test_refresh_failure_marks_disconnected(db_session):
    op = Operacao(nome="Refresh Fail")
    _wire_operacao_mp(op, access_token=_TOKEN_A, oauth_user_id="333")
    op.mercadopago_oauth_expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db_session.add(op)
    db_session.commit()

    with patch(
        "motopay.services.mercadopago_token_service.refresh_oauth_token",
        side_effect=MercadoPagoApiError(400, "refresh failed"),
    ):
        with pytest.raises(MercadoPagoNotConnectedError):
            ensure_valid_mp_token(db_session, op)

    db_session.refresh(op)
    assert op.mercadopago_connection_status == "disconnected"
    assert op.mercadopago_access_token is None


def test_refresh_success_updates_token(db_session):
    new_token = "APP_USR-cccccccccccccccc-new"
    op = Operacao(nome="Refresh OK")
    _wire_operacao_mp(op, access_token=_TOKEN_A, oauth_user_id="444")
    op.mercadopago_oauth_expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db_session.add(op)
    db_session.commit()

    with patch(
        "motopay.services.mercadopago_token_service.refresh_oauth_token",
        return_value={
            "access_token": new_token,
            "refresh_token": "refresh-new",
            "expires_in": 3600,
            "public_key": _PUBLIC_KEY,
        },
    ):
        token = ensure_valid_mp_token(db_session, op)

    assert token == new_token
    db_session.refresh(op)
    assert op.mercadopago_connection_status == "connected"


def test_disconnected_operacao_raises_on_payment(db_session):
    op = Operacao(nome="Disconnected", mercadopago_connection_status="disconnected")
    db_session.add(op)
    db_session.flush()
    with pytest.raises(MercadoPagoNotConnectedError):
        require_operacao_mp_token(db_session, op)
