from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from motopay.domain.enums import (
    CicloCobranca,
    CobrancaStatus,
    ContratoStatus,
    DomainEventType,
)
from motopay.infrastructure.db.models import (
    Cliente,
    Cobranca,
    Contrato,
    EventoDominio,
    Moto,
    Operacao,
)
from motopay.infrastructure.messaging import tasks as messaging_tasks
from motopay.infrastructure.telegram.templates import build_overdue_html
from motopay.services.billing_service import refresh_overdue_pix
from motopay.services.late_fee import calculate_late_amounts
from motopay.services.payment_gateway import PixOrderResult
from sqlalchemy import select


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
def moto_alugada(db_session, operacao_multas):
    m = Moto(
        operacao_id=operacao_multas.id,
        placa="XYZ9Z99",
        modelo="Biz 125",
        status="alugada",
    )
    db_session.add(m)
    db_session.flush()
    return m


@pytest.fixture
def contrato_atrasado(db_session, operacao_multas, cliente_com_telegram, moto_alugada):
    today = date.today()
    ct = Contrato(
        operacao_id=operacao_multas.id,
        cliente_id=cliente_com_telegram.id,
        moto_id=moto_alugada.id,
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


@pytest.fixture
def cobranca_pendente(db_session, operacao_multas, contrato_atrasado):
    cob = Cobranca(
        operacao_id=operacao_multas.id,
        contrato_id=contrato_atrasado.id,
        valor=Decimal("350.00"),
        vencimento=contrato_atrasado.proximo_vencimento,
        mercadopago_order_id="ORD_old_123",
        mercadopago_payment_id="pay_old_123",
        pix_copia_cola="PIX-OLD-CODE",
        status=CobrancaStatus.PENDENTE.value,
    )
    db_session.add(cob)
    db_session.flush()
    return cob


def test_calculate_late_amounts():
    op = Operacao(
        nome="Op Multas",
        multa_fixa_percentual=Decimal("2.00"),
        juros_diario_percentual=Decimal("0.10"),
    )
    today = date(2026, 1, 10)
    venc = date(2026, 1, 7)
    amounts = calculate_late_amounts(
        valor_base=Decimal("350.00"),
        vencimento=venc,
        operacao=op,
        today=today,
    )
    assert amounts.dias_atraso == 3
    assert amounts.multa == Decimal("7.00")
    assert amounts.juros == Decimal("1.05")
    assert amounts.valor_total == Decimal("358.05")


def test_refresh_skips_when_total_unchanged(
    db_session, operacao_multas, contrato_atrasado, cobranca_pendente
):
    today = date.today()
    amounts = calculate_late_amounts(
        valor_base=contrato_atrasado.valor_recorrente,
        vencimento=contrato_atrasado.proximo_vencimento,
        operacao=operacao_multas,
        today=today,
    )
    cobranca_pendente.valor = amounts.valor_total
    cobranca_pendente.status = CobrancaStatus.ATRASADO.value
    cobranca_pendente.mercadopago_order_id = "ORD_current"
    cobranca_pendente.mercadopago_payment_id = "pay_current"
    cobranca_pendente.pix_copia_cola = "PIX-CURRENT"
    db_session.add(cobranca_pendente)
    db_session.flush()

    with patch("motopay.services.payment_gateway.MercadoPagoClient") as mock_cls:
        result = refresh_overdue_pix(db_session, contrato=contrato_atrasado, today=today)
        mock_cls.assert_not_called()

    assert result is not None
    assert result.mercadopago_order_id == "ORD_current"


def test_refresh_cancels_and_creates_new_pix(
    db_session, operacao_multas, contrato_atrasado, cobranca_pendente, cliente_com_telegram
):
    today = date.today()
    new_order = PixOrderResult(
        order_id="ORD_new_456",
        payment_id="pay_new_456",
        pix_copia_cola="PIX-NEW-CODE",
    )
    mock_client = MagicMock()
    mock_client.create_online_order.return_value = MagicMock(
        order_id=new_order.order_id,
        payment_id=new_order.payment_id,
        pix_copia_cola=new_order.pix_copia_cola,
    )

    with patch(
        "motopay.services.payment_gateway.mp_configured_for_operacao", return_value=True
    ), patch(
        "motopay.services.payment_gateway.MercadoPagoClient", return_value=mock_client
    ):
        cob = refresh_overdue_pix(db_session, contrato=contrato_atrasado, today=today)

    mock_client.create_online_order.assert_called_once()
    assert cob is not None
    assert cob.mercadopago_order_id == "ORD_new_456"
    assert cob.mercadopago_payment_id == "pay_new_456"
    assert cob.pix_copia_cola == "PIX-NEW-CODE"
    assert cob.status == CobrancaStatus.ATRASADO.value
    assert cob.valor > Decimal("350.00")


def test_process_delinquency_payload_includes_pix(
    db_session, operacao_multas, contrato_atrasado, cliente_com_telegram
):
    today = date.today()
    fake_cob = Cobranca(
        operacao_id=operacao_multas.id,
        contrato_id=contrato_atrasado.id,
        valor=Decimal("358.05"),
        vencimento=contrato_atrasado.proximo_vencimento,
        mercadopago_payment_id="pay_x",
        pix_copia_cola="PIX-FROM-REFRESH",
        status=CobrancaStatus.ATRASADO.value,
    )
    db_session.add(fake_cob)
    db_session.flush()

    with patch(
        "motopay.infrastructure.messaging.tasks.refresh_overdue_pix",
        return_value=fake_cob,
    ):
        with patch("motopay.infrastructure.messaging.tasks.handle_domain_event.delay"):
            messaging_tasks._process_delinquency(db_session, today)

    ev = db_session.scalars(
        select(EventoDominio).where(
            EventoDominio.tipo == DomainEventType.CLIENTE_INADIMPLENTE.value
        )
    ).first()
    assert ev is not None
    assert ev.payload["pix_copia_cola"] == "PIX-FROM-REFRESH"
    assert ev.payload["valor_total"] is not None


def test_build_overdue_telegram_message_includes_pix():
    payload = {
        "dias_atraso": 3,
        "valor_base": "350.00",
        "multa": "7.00",
        "juros": "1.05",
        "valor_total": "358.05",
        "pix_copia_cola": "PIX-TEST-CODE-123",
    }
    html = build_overdue_html(overrides=None, payload=payload, nivel=1)
    assert "PIX-TEST-CODE-123" in html
    assert "358,05" in html
    assert "<code>" in html


def test_handle_domain_event_sends_pix_message(db_session, cliente_com_telegram):
    ev = EventoDominio(
        tipo=DomainEventType.CLIENTE_INADIMPLENTE.value,
        payload={
            "cliente_id": cliente_com_telegram.id,
            "operacao_id": cliente_com_telegram.operacao_id,
            "nivel_escalonamento": 1,
            "dias_atraso": 3,
            "valor_base": "350.00",
            "multa": "7.00",
            "juros": "1.05",
            "valor_total": "358.05",
            "pix_copia_cola": "PIX-TEST-CODE-123",
        },
    )
    db_session.add(ev)
    db_session.flush()

    with patch.object(db_session, "close", MagicMock()):
        with patch(
            "motopay.infrastructure.messaging.tasks.SessionLocal",
            return_value=db_session,
        ):
            with patch(
                "motopay.infrastructure.messaging.tasks.send_telegram_html",
            ) as mock_send:
                messaging_tasks.handle_domain_event.run(ev.id)

    mock_send.assert_called_once()
    html = mock_send.call_args.kwargs["html"]
    assert "PIX-TEST-CODE-123" in html
    assert "358,05" in html
