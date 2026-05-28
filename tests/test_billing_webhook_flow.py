from __future__ import annotations

from datetime import date
from decimal import Decimal

from motopay.domain.enums import CicloCobranca, CobrancaStatus, ContratoStatus, DomainEventType
from motopay.infrastructure.db.models import (
    Cliente,
    Cobranca,
    Contrato,
    EventoDominio,
    Moto,
    Operacao,
)
from motopay.services.billing_service import handle_mercadopago_payment_confirmed
from sqlalchemy import func, select


def _setup_cobranca(
    db_session, *, mercadopago_payment_id: str = "pay_idempotent_1"
) -> Cobranca:
    op = Operacao(nome="Billing Op")
    db_session.add(op)
    db_session.flush()
    cl = Cliente(
        operacao_id=op.id,
        nome="Cliente Billing",
        cpf="12345678901",
        telefone="11988887777",
    )
    db_session.add(cl)
    db_session.flush()
    moto = Moto(operacao_id=op.id, placa="BIL1L11", modelo="Biz", status="alugada")
    db_session.add(moto)
    db_session.flush()
    ct = Contrato(
        operacao_id=op.id,
        cliente_id=cl.id,
        moto_id=moto.id,
        valor_recorrente=Decimal("200"),
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
        valor=Decimal("200"),
        vencimento=date(2025, 2, 1),
        mercadopago_payment_id=mercadopago_payment_id,
        status=CobrancaStatus.PENDENTE.value,
    )
    db_session.add(cob)
    db_session.commit()
    return cob


def test_handle_mercadopago_payment_confirmed_marks_cobranca_received(db_session):
    cob = _setup_cobranca(db_session)
    found, ev_id = handle_mercadopago_payment_confirmed(
        db_session, mercadopago_payment_id=cob.mercadopago_payment_id
    )
    assert found is True
    assert ev_id is not None
    db_session.refresh(cob)
    assert cob.status == CobrancaStatus.RECEBIDO.value


def test_handle_mercadopago_payment_confirmed_is_idempotent(db_session):
    cob = _setup_cobranca(db_session, mercadopago_payment_id="pay_idempotent_2")
    first_found, first_ev_id = handle_mercadopago_payment_confirmed(
        db_session, mercadopago_payment_id=cob.mercadopago_payment_id
    )
    second_found, second_ev_id = handle_mercadopago_payment_confirmed(
        db_session, mercadopago_payment_id=cob.mercadopago_payment_id
    )
    assert first_found is True
    assert first_ev_id is not None
    assert second_found is True
    assert second_ev_id is None
    event_count = db_session.scalar(
        select(func.count())
        .select_from(EventoDominio)
        .where(EventoDominio.tipo == DomainEventType.PAGAMENTO_CONFIRMADO.value)
    )
    assert event_count == 1


def test_handle_mercadopago_payment_confirmed_unknown_payment_returns_false(db_session):
    found, ev_id = handle_mercadopago_payment_confirmed(
        db_session, mercadopago_payment_id="pay_missing"
    )
    assert found is False
    assert ev_id is None
