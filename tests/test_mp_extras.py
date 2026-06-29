from __future__ import annotations

from datetime import date
from decimal import Decimal

from motopay.domain.enums import CicloCobranca, CobrancaStatus, ContratoStatus
from motopay.infrastructure.db.models import Cliente, Cobranca, Contrato, Moto, Operacao
from motopay.infrastructure.payments.mercadopago_client import MercadoPagoClient
from motopay.services.billing_service import charge_amounts_for_cobranca


def test_preapproval_frequency_weekly():
    assert MercadoPagoClient.preapproval_frequency("semanal") == (1, "weeks")


def test_preapproval_frequency_monthly():
    assert MercadoPagoClient.preapproval_frequency("mensal") == (1, "months")


def test_charge_amounts_includes_late_fees(db_session):
    op = Operacao(nome="Op", multa_fixa_percentual=Decimal("10"), juros_diario_percentual=Decimal("1"))
    db_session.add(op)
    db_session.flush()
    cl = Cliente(operacao_id=op.id, nome="C", cpf="111", telefone="11")
    db_session.add(cl)
    db_session.flush()
    m = Moto(operacao_id=op.id, placa="ABC1D23", modelo="X", status="alugada")
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
        proximo_vencimento=date(2025, 1, 1),
    )
    db_session.add(ct)
    db_session.flush()
    cob = Cobranca(
        operacao_id=op.id,
        contrato_id=ct.id,
        valor=Decimal("100"),
        vencimento=date(2025, 1, 1),
        status=CobrancaStatus.PENDENTE.value,
    )
    db_session.add(cob)
    db_session.flush()
    amounts = charge_amounts_for_cobranca(cob, ct, op, date(2025, 1, 11))
    assert amounts.dias_atraso == 10
    assert amounts.valor_total > Decimal("100")
