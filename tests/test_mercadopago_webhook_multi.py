from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from motopay.config import get_settings
from motopay.domain.enums import CicloCobranca, CobrancaStatus, ContratoStatus
from motopay.infrastructure.db.models import Cliente, Cobranca, Contrato, Moto, Operacao
from tests.test_mercadopago_client import _signature_headers


def _seed_cobranca_with_operacao(db_session, *, order_id: str, webhook_secret: str) -> Operacao:
    op = Operacao(
        nome="MP Op",
        mercadopago_access_token="op-tok",
        mercadopago_public_key="op-pk",
        mercadopago_webhook_secret=webhook_secret,
    )
    db_session.add(op)
    db_session.flush()
    cl = Cliente(
        operacao_id=op.id,
        nome="Test",
        cpf="11122233344",
        telefone="11999999999",
    )
    db_session.add(cl)
    db_session.flush()
    m = Moto(operacao_id=op.id, placa="XYZ9Z99", modelo="Biz", status="alugada")
    db_session.add(m)
    db_session.flush()
    ct = Contrato(
        operacao_id=op.id,
        cliente_id=cl.id,
        moto_id=m.id,
        valor_recorrente=Decimal("100"),
        ciclo=CicloCobranca.MENSAL.value,
        status=ContratoStatus.ATIVO.value,
        data_inicio=date(2025, 1, 1),
        proximo_vencimento=date(2025, 2, 1),
    )
    db_session.add(ct)
    db_session.flush()
    cob = Cobranca(
        operacao_id=op.id,
        contrato_id=ct.id,
        valor=Decimal("100"),
        vencimento=date(2025, 2, 1),
        mercadopago_order_id=order_id,
        mercadopago_payment_id="PAY-op",
        payment_gateway="mercadopago",
        status=CobrancaStatus.PENDENTE.value,
    )
    db_session.add(cob)
    db_session.commit()
    return op


def test_webhook_rejects_global_secret_when_operacao_secret_required(
    client, db_session, monkeypatch
):
    monkeypatch.setenv("MERCADOPAGO_WEBHOOK_SECRET", "global-secret")
    get_settings.cache_clear()

    order_id = "ORD-op-1"
    _seed_cobranca_with_operacao(db_session, order_id=order_id, webhook_secret="op-secret")

    headers = _signature_headers(secret="global-secret", data_id=order_id)
    r = client.post(
        "/webhooks/mercadopago",
        headers=headers,
        json={"type": "order", "data": {"id": order_id}},
    )
    assert r.status_code == 403
    get_settings.cache_clear()


def test_webhook_accepts_operacao_secret(client, db_session, monkeypatch):
    monkeypatch.setenv("MERCADOPAGO_WEBHOOK_SECRET", "global-secret")
    get_settings.cache_clear()

    order_id = "ORD-op-2"
    _seed_cobranca_with_operacao(db_session, order_id=order_id, webhook_secret="op-secret")

    headers = _signature_headers(secret="op-secret", data_id=order_id)
    with (
        patch(
            "motopay.interfaces.api.routers.webhooks._order_confirmed_in_mercadopago",
            return_value=(True, Decimal("100")),
        ) as mock_confirm,
        patch("motopay.interfaces.api.routers.webhooks.handle_domain_event") as mock_task,
    ):
        mock_task.delay = MagicMock()
        r = client.post(
            "/webhooks/mercadopago",
            headers=headers,
            json={"type": "order", "data": {"id": order_id}},
        )
    assert r.status_code == 200
    mock_confirm.assert_called_once()
    assert mock_confirm.call_args.kwargs["op"] is not None
    assert mock_confirm.call_args.kwargs["op"].mercadopago_webhook_secret == "op-secret"
    get_settings.cache_clear()
