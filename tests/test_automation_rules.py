from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from motopay.domain.enums import CobrancaStatus, ContratoStatus
from motopay.infrastructure.db.models import Cliente, Cobranca, Contrato, Operacao
from motopay.infrastructure.messaging import tasks as messaging_tasks
from motopay.services.billing_service import handle_mercadopago_order_confirmed
from motopay.services.scoring_service import effective_escalation_level


def test_effective_escalation_high_score_reduces_level():
    assert effective_escalation_level(2, 85) == 1
    assert effective_escalation_level(0, 90) == 0


def test_effective_escalation_low_score_firms():
    assert effective_escalation_level(0, 30) == 1
    assert effective_escalation_level(1, 20) == 2


def test_promessa_skips_telegram_in_delinquency(db_session, operacao_multas, contrato_atrasado):
    contrato_atrasado.promessa_pagamento_em = date.today() + timedelta(days=2)
    db_session.add(contrato_atrasado)
    db_session.commit()

    with patch.object(messaging_tasks, "handle_domain_event") as mock_delay:
        messaging_tasks._process_delinquency(db_session, today=date.today())
        mock_delay.delay.assert_not_called()


def test_dedup_skips_same_day_telegram(
    db_session, operacao_multas, contrato_atrasado, cliente_com_telegram
):
    contrato_atrasado.inadimplente = True
    contrato_atrasado.ultima_cobranca_telegram_em = date.today()
    db_session.add(contrato_atrasado)
    db_session.commit()

    with patch.object(messaging_tasks, "handle_domain_event") as mock_delay:
        messaging_tasks._process_delinquency(db_session, today=date.today())
        mock_delay.delay.assert_not_called()


def test_contract_expiry_finalizes_active(db_session, contrato_atrasado):
    today = date.today()
    contrato_atrasado.data_fim_vigencia = today - timedelta(days=1)
    db_session.add(contrato_atrasado)
    db_session.commit()

    messaging_tasks._process_contract_expiry(db_session, today=today)
    db_session.refresh(contrato_atrasado)
    assert contrato_atrasado.status == ContratoStatus.FINALIZADO.value


def test_contract_expiry_skips_without_end_date(db_session, contrato_atrasado):
    today = date.today()
    contrato_atrasado.data_fim_vigencia = None
    db_session.add(contrato_atrasado)
    db_session.commit()

    messaging_tasks._process_contract_expiry(db_session, today=today)
    db_session.refresh(contrato_atrasado)
    assert contrato_atrasado.status == ContratoStatus.ATIVO.value


def test_payment_clears_promessa(
    db_session, operacao_multas, contrato_atrasado, cliente_com_telegram
):
    contrato_atrasado.promessa_pagamento_em = date.today()
    contrato_atrasado.promessa_notas = "pagar sexta"
    db_session.add(contrato_atrasado)
    cob = Cobranca(
        operacao_id=operacao_multas.id,
        contrato_id=contrato_atrasado.id,
        valor=Decimal("350.00"),
        vencimento=contrato_atrasado.proximo_vencimento,
        mercadopago_order_id="ORD_test_123",
        mercadopago_payment_id="pay_test_123",
        status=CobrancaStatus.PENDENTE.value,
    )
    db_session.add(cob)
    db_session.commit()

    handle_mercadopago_order_confirmed(db_session, mercadopago_order_id="ORD_test_123")
    db_session.refresh(contrato_atrasado)
    assert contrato_atrasado.promessa_pagamento_em is None
    assert contrato_atrasado.promessa_notas is None


@pytest.fixture
def operacao_multas(db_session):
    op = Operacao(
        nome="Op Multas",
        multa_fixa_percentual=Decimal("2.00"),
        juros_diario_percentual=Decimal("0.10"),
    )
    db_session.add(op)
    db_session.flush()
    return op


@pytest.fixture
def cliente_com_telegram(db_session, operacao_multas):
    c = Cliente(
        operacao_id=operacao_multas.id,
        nome="João",
        cpf="12345678901",
        telefone="11999999999",
        telegram_id="123456789",
    )
    db_session.add(c)
    db_session.flush()
    return c


@pytest.fixture
def contrato_atrasado(db_session, operacao_multas, cliente_com_telegram):
    from motopay.domain.enums import CicloCobranca
    from motopay.infrastructure.db.models import Moto

    m = Moto(operacao_id=operacao_multas.id, placa="ABC1D23", modelo="Biz", status="alugada")
    db_session.add(m)
    db_session.flush()
    today = date.today()
    ct = Contrato(
        operacao_id=operacao_multas.id,
        cliente_id=cliente_com_telegram.id,
        moto_id=m.id,
        valor_recorrente=Decimal("350.00"),
        ciclo=CicloCobranca.MENSAL.value,
        status=ContratoStatus.ATIVO.value,
        data_inicio=today - timedelta(days=40),
        proximo_vencimento=today - timedelta(days=3),
        inadimplente=False,
    )
    db_session.add(ct)
    db_session.flush()
    return ct
