from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from motopay.domain.enums import CicloCobranca, CobrancaStatus, ContratoStatus
from motopay.infrastructure.db.models import Cliente, Cobranca, Contrato, Moto, Operacao


def test_mercadopago_webhook_confirms_payment(client, db_session):
    op = Operacao(nome="MP Op")
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
        mercadopago_payment_id="999888",
        payment_gateway="mercadopago",
        status=CobrancaStatus.PENDENTE.value,
    )
    db_session.add(cob)
    db_session.commit()

    with (
        patch(
            "motopay.interfaces.api.routers.webhooks._payment_confirmed_in_mercadopago",
            return_value=(True, Decimal("100")),
        ),
        patch("motopay.interfaces.api.routers.webhooks.handle_domain_event") as mock_task,
    ):
        mock_task.delay = MagicMock()
        r = client.post("/webhooks/mercadopago", json={"type": "payment", "data": {"id": "999888"}})
        assert r.status_code == 200
        db_session.refresh(cob)
        assert cob.status == CobrancaStatus.RECEBIDO.value
