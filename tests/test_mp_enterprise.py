from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from motopay.domain.enums import CicloCobranca, CobrancaStatus, ContratoStatus
from motopay.infrastructure.db.models import (
    Cliente,
    ClienteMpCard,
    Cobranca,
    Contrato,
    Financeiro,
    Moto,
    Operacao,
)
from motopay.services.billing_service import (
    handle_mercadopago_chargeback,
    handle_mercadopago_refund_confirmed,
    handle_mercadopago_subscription_payment,
    sync_refund_from_mercadopago_payment,
)
from sqlalchemy import select

from tests.conftest import auth_header, login


def _seed_received_cobranca(db_session):
    op = Operacao(
        nome="Enterprise Op",
        mercadopago_access_token="TEST-token",
        mercadopago_public_key="TEST-pk",
        mercadopago_webhook_secret="whsec",
    )
    db_session.add(op)
    db_session.flush()
    cl = Cliente(
        operacao_id=op.id,
        nome="Cliente Portal",
        cpf="12345678901",
        telefone="11999990000",
        email="cliente@test.local",
    )
    db_session.add(cl)
    db_session.flush()
    m = Moto(operacao_id=op.id, placa="ENT1E11", modelo="Biz", status="alugada")
    db_session.add(m)
    db_session.flush()
    ct = Contrato(
        operacao_id=op.id,
        cliente_id=cl.id,
        moto_id=m.id,
        valor_recorrente=Decimal("150"),
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
        valor=Decimal("150"),
        vencimento=date(2025, 2, 1),
        mercadopago_payment_id="pay-enterprise-1",
        payment_gateway="mercadopago",
        status=CobrancaStatus.PENDENTE.value,
        payment_portal_token="portal-token-test",
    )
    db_session.add(cob)
    db_session.commit()
    return op, cob


def test_public_portal_checkout(client, db_session):
    op, cob = _seed_received_cobranca(db_session)
    r = client.get(f"/api/v1/public/pay/{cob.payment_portal_token}")
    assert r.status_code == 200
    data = r.json()
    assert data["cliente_nome"] == "Cliente Portal"
    assert data["payable"] is True
    assert data["cobranca"]["id"] == cob.id
    assert data["mercadopago_public_key"] == op.mercadopago_public_key


def test_portal_expired_returns_403(client, db_session):
    _, cob = _seed_received_cobranca(db_session)
    cob.payment_portal_expires_at = datetime.now(UTC) - timedelta(days=1)
    db_session.add(cob)
    db_session.commit()
    r = client.get(f"/api/v1/public/pay/{cob.payment_portal_token}")
    assert r.status_code == 403


def test_public_portal_cards(client, db_session):
    op, cob = _seed_received_cobranca(db_session)
    ct = db_session.get(Contrato, cob.contrato_id)
    card = ClienteMpCard(
        cliente_id=ct.cliente_id,
        operacao_id=op.id,
        mp_card_id="card-mp-1",
        last_four_digits="4242",
        payment_method_id="visa",
        is_default=True,
    )
    db_session.add(card)
    db_session.commit()
    r = client.get(f"/api/v1/public/pay/{cob.payment_portal_token}/cards")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["last_four_digits"] == "4242"


def test_portal_link_requires_auth(client, db_session, dono_user):
    _, cob = _seed_received_cobranca(db_session)
    token = login(client, dono_user.email, "donodono")["access_token"]
    r = client.post(
        f"/api/v1/cobrancas/{cob.id}/portal-link",
        headers=auth_header(token),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["token"]
    assert "/pay/" in body["url"]


def test_partial_refund_updates_valor_estornado(db_session):
    _, cob = _seed_received_cobranca(db_session)
    cob.status = CobrancaStatus.RECEBIDO.value
    db_session.add(cob)
    db_session.commit()

    ok, _ = handle_mercadopago_refund_confirmed(
        db_session,
        mercadopago_payment_id="pay-enterprise-1",
        refund_amount=Decimal("50"),
    )
    assert ok
    db_session.refresh(cob)
    assert cob.valor_estornado == Decimal("50")
    assert cob.status == CobrancaStatus.RECEBIDO.value

    ok2, _ = handle_mercadopago_refund_confirmed(
        db_session,
        mercadopago_payment_id="pay-enterprise-1",
        refund_amount=Decimal("100"),
    )
    assert ok2
    db_session.refresh(cob)
    assert cob.valor_estornado == Decimal("150")
    assert cob.status == CobrancaStatus.CANCELADO.value


def test_sync_refund_from_payment_webhook(db_session):
    _, cob = _seed_received_cobranca(db_session)
    cob.status = CobrancaStatus.RECEBIDO.value
    db_session.add(cob)
    db_session.commit()

    sync_refund_from_mercadopago_payment(
        db_session,
        pay_data={
            "id": "pay-enterprise-1",
            "status": "partially_refunded",
            "transaction_amount_refunded": 40.0,
        },
    )
    db_session.refresh(cob)
    assert cob.valor_estornado == Decimal("40")


def test_chargeback_lost_creates_financeiro_idempotent(db_session):
    _, cob = _seed_received_cobranca(db_session)
    cob.status = CobrancaStatus.RECEBIDO.value
    db_session.add(cob)
    db_session.commit()

    ok, _ = handle_mercadopago_chargeback(
        db_session,
        chargeback_data={
            "payment_id": "pay-enterprise-1",
            "status": "lost",
            "amount": 150.0,
        },
    )
    assert ok
    fins = db_session.scalars(
        select(Financeiro).where(Financeiro.operacao_id == cob.operacao_id)
    ).all()
    assert len(fins) == 1
    assert fins[0].valor == Decimal("150")

    ok2, _ = handle_mercadopago_chargeback(
        db_session,
        chargeback_data={
            "payment_id": "pay-enterprise-1",
            "status": "lost",
            "amount": 150.0,
        },
    )
    assert ok2
    fins2 = db_session.scalars(
        select(Financeiro).where(Financeiro.operacao_id == cob.operacao_id)
    ).all()
    assert len(fins2) == 1


def test_subscription_payment_uses_late_amounts(db_session):
    op = Operacao(
        nome="Late Sub",
        multa_fixa_percentual=Decimal("10"),
        juros_diario_percentual=Decimal("1"),
    )
    db_session.add(op)
    db_session.flush()
    cl = Cliente(
        operacao_id=op.id,
        nome="Late",
        cpf="55566677788",
        telefone="11666660000",
    )
    db_session.add(cl)
    db_session.flush()
    m = Moto(operacao_id=op.id, placa="LAT1E11", modelo="Biz", status="alugada")
    db_session.add(m)
    db_session.flush()
    past_due = date.today() - timedelta(days=10)
    ct = Contrato(
        operacao_id=op.id,
        cliente_id=cl.id,
        moto_id=m.id,
        valor_recorrente=Decimal("100"),
        ciclo=CicloCobranca.MENSAL.value,
        status=ContratoStatus.ATIVO.value,
        data_inicio=past_due - timedelta(days=30),
        proximo_vencimento=past_due,
        mercadopago_subscription_id="pre-late",
    )
    db_session.add(ct)
    db_session.commit()

    found, _ = handle_mercadopago_subscription_payment(
        db_session,
        mercadopago_payment_id="pay-sub-late",
        pay_data={
            "preapproval_id": "pre-late",
            "transaction_amount": 120,
            "status": "approved",
        },
        value=Decimal("120"),
    )
    assert found
    cob = db_session.scalars(
        select(Cobranca).where(Cobranca.mercadopago_payment_id == "pay-sub-late")
    ).first()
    assert cob is not None
    assert cob.valor > Decimal("100")


def test_chargeback_sets_dispute_status(db_session):
    _, cob = _seed_received_cobranca(db_session)
    cob.status = CobrancaStatus.RECEBIDO.value
    db_session.add(cob)
    db_session.commit()

    ok, _ = handle_mercadopago_chargeback(
        db_session,
        chargeback_data={"payment_id": "pay-enterprise-1", "status": "opened"},
    )
    assert ok
    db_session.refresh(cob)
    assert cob.mercadopago_dispute_status == "opened"


def test_webhook_chargeback_topic(client, db_session):
    _, cob = _seed_received_cobranca(db_session)
    cob.status = CobrancaStatus.RECEBIDO.value
    db_session.add(cob)
    db_session.commit()

    with patch(
        "motopay.interfaces.api.routers.webhooks.MercadoPagoClient"
    ) as mock_cls:
        mock_cls.return_value.get_chargeback.return_value = {
            "payment_id": "pay-enterprise-1",
            "status": "under_review",
        }
        r = client.post(
            "/webhooks/mercadopago",
            json={"type": "chargeback", "data": {"id": "cb-1"}},
        )
    assert r.status_code == 200
    db_session.refresh(cob)
    assert cob.mercadopago_dispute_status == "under_review"


def test_update_contrato_syncs_subscription_amount(
    client, db_session, dono_user, operacao_a
):
    cl = Cliente(
        operacao_id=operacao_a.id,
        nome="Sub",
        cpf="98765432100",
        telefone="11888880000",
    )
    db_session.add(cl)
    db_session.flush()
    m = Moto(operacao_id=operacao_a.id, placa="SUB1S11", modelo="Fan", status="alugada")
    db_session.add(m)
    db_session.flush()
    ct = Contrato(
        operacao_id=operacao_a.id,
        cliente_id=cl.id,
        moto_id=m.id,
        valor_recorrente=Decimal("200"),
        ciclo=CicloCobranca.MENSAL.value,
        status=ContratoStatus.ATIVO.value,
        data_inicio=date(2025, 1, 1),
        proximo_vencimento=date(2025, 2, 1),
        mercadopago_subscription_id="pre-123",
    )
    db_session.add(ct)
    operacao_a.mercadopago_access_token = "tok"
    operacao_a.mercadopago_public_key = "pk"
    operacao_a.mercadopago_webhook_secret = "sec"
    db_session.add(operacao_a)
    db_session.commit()

    token = login(client, dono_user.email, "donodono")["access_token"]
    with patch(
        "motopay.services.billing_service.MercadoPagoClient"
    ) as mock_cls:
        mock_cls.return_value.update_preapproval_amount = MagicMock()
        r = client.patch(
            f"/api/v1/contratos/{ct.id}",
            headers=auth_header(token),
            json={"valor_recorrente": "250.00"},
        )
    assert r.status_code == 200
    mock_cls.return_value.update_preapproval_amount.assert_called_once()


def test_update_contrato_syncs_ciclo(client, db_session, dono_user, operacao_a):
    cl = Cliente(
        operacao_id=operacao_a.id,
        nome="Sub Ciclo",
        cpf="11122233344",
        telefone="11777770000",
    )
    db_session.add(cl)
    db_session.flush()
    m = Moto(operacao_id=operacao_a.id, placa="CIC1L11", modelo="Fan", status="alugada")
    db_session.add(m)
    db_session.flush()
    ct = Contrato(
        operacao_id=operacao_a.id,
        cliente_id=cl.id,
        moto_id=m.id,
        valor_recorrente=Decimal("200"),
        ciclo=CicloCobranca.MENSAL.value,
        status=ContratoStatus.ATIVO.value,
        data_inicio=date(2025, 1, 1),
        proximo_vencimento=date(2025, 2, 1),
        mercadopago_subscription_id="pre-456",
    )
    db_session.add(ct)
    operacao_a.mercadopago_access_token = "tok"
    operacao_a.mercadopago_public_key = "pk"
    operacao_a.mercadopago_webhook_secret = "sec"
    db_session.add(operacao_a)
    db_session.commit()

    token = login(client, dono_user.email, "donodono")["access_token"]
    with patch(
        "motopay.services.billing_service.MercadoPagoClient"
    ) as mock_cls:
        mock_cls.return_value.update_preapproval_amount = MagicMock()
        r = client.patch(
            f"/api/v1/contratos/{ct.id}",
            headers=auth_header(token),
            json={"ciclo": "semanal"},
        )
    assert r.status_code == 200
    mock_cls.return_value.update_preapproval_amount.assert_called_once()
