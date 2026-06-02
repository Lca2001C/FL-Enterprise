from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from motopay.infrastructure.db.models import Cliente, Operacao
from motopay.domain.exceptions import ForbiddenError
from motopay.infrastructure.payments.mercadopago_sdk import MercadoPagoApiError
from motopay.infrastructure.payments.order_utils import MercadoPagoOrderResult
from motopay.services.payment_gateway import create_pix_for_cobranca


def test_create_pix_propagates_mercadopago_api_error():
    op = Operacao(
        nome="Op",
        mercadopago_access_token="tok",
        mercadopago_public_key="pk",
        mercadopago_webhook_secret="sec",
    )
    cliente = Cliente(
        operacao_id=1,
        nome="C",
        cpf="12345678901",
        telefone="11999999999",
    )
    with patch(
        "motopay.services.payment_gateway.MercadoPagoClient",
    ) as mock_cls:
        mock_cls.return_value.create_online_order.side_effect = MercadoPagoApiError(
            400, "bad request"
        )
        with pytest.raises(ForbiddenError, match="Falha ao criar Pix"):
            create_pix_for_cobranca(
                op=op,
                cliente=cliente,
                cobranca_id=1,
                valor_total=Decimal("50"),
                due_date=date.today(),
            )


def test_create_pix_returns_order_and_payment_ids():
    op = Operacao(
        nome="Op",
        mercadopago_access_token="tok",
        mercadopago_public_key="pk",
        mercadopago_webhook_secret="sec",
    )
    cliente = Cliente(
        operacao_id=1,
        nome="C",
        cpf="12345678901",
        telefone="11999999999",
    )
    order = MercadoPagoOrderResult(
        order_id="ORD1",
        payment_id="PAY1",
        order_status="action_required",
        payment_status="action_required",
        status_detail="waiting_transfer",
        pix_copia_cola="pixcode",
        three_ds_info=None,
        requires_3ds=False,
    )
    with patch(
        "motopay.services.payment_gateway.MercadoPagoClient",
        return_value=MagicMock(create_online_order=MagicMock(return_value=order)),
    ):
        order_id, payment_id, pix, gw = create_pix_for_cobranca(
            op=op,
            cliente=cliente,
            cobranca_id=42,
            valor_total=Decimal("50"),
            due_date=date.today(),
        )
    assert order_id == "ORD1"
    assert payment_id == "PAY1"
    assert pix == "pixcode"
    assert gw == "mercadopago"
