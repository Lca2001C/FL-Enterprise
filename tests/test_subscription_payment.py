from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select

from motopay.domain.enums import CicloCobranca, CobrancaStatus, ContratoStatus
from motopay.infrastructure.db.models import Cliente, Cobranca, Contrato, Moto, Operacao
from motopay.services.billing_service import handle_mercadopago_subscription_payment


def test_subscription_payment_creates_and_confirms_cobranca(db_session):
    op = Operacao(nome="Op")
    db_session.add(op)
    db_session.flush()
    cl = Cliente(
        operacao_id=op.id,
        nome="C",
        cpf="11122233344",
        telefone="11999999999",
    )
    db_session.add(cl)
    db_session.flush()
    m = Moto(operacao_id=op.id, placa="ABC1D23", modelo="Biz", status="alugada")
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
        mercadopago_subscription_id="pre-123",
    )
    db_session.add(ct)
    db_session.commit()

    found, ev_id = handle_mercadopago_subscription_payment(
        db_session,
        mercadopago_payment_id="pay-sub-1",
        pay_data={
            "preapproval_id": "pre-123",
            "transaction_amount": 100,
            "status": "approved",
        },
        value=Decimal("100"),
    )
    assert found is True
    assert ev_id is not None
    cob = db_session.scalars(
        select(Cobranca).where(Cobranca.mercadopago_payment_id == "pay-sub-1")
    ).first()
    assert cob is not None
    assert cob.status == CobrancaStatus.RECEBIDO.value
