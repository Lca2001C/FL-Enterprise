from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from motopay.domain.enums import CicloCobranca, CobrancaStatus, ContratoStatus, UserRole
from motopay.interfaces.api.deps import CurrentUser
from motopay.infrastructure.db.models import Cliente, Cobranca, Contrato, Moto, Operacao
from motopay.infrastructure.payments.order_utils import MercadoPagoOrderResult, ThreeDsInfo
from motopay.services.card_payment_service import pay_cobranca_with_card, save_cliente_card
from tests.conftest import auth_header, login


def _dono_current(user) -> CurrentUser:
    return CurrentUser(
        id=user.id,
        email=user.email,
        role=UserRole.DONO,
        operacao_id=user.operacao_id,
    )


def _seed_cobranca(db_session, *, operacao: Operacao) -> tuple[Cobranca, Cliente]:
    operacao.mercadopago_access_token = "tok"
    operacao.mercadopago_public_key = "pk"
    operacao.mercadopago_webhook_secret = "wh"
    db_session.add(operacao)
    db_session.flush()
    cl = Cliente(
        operacao_id=operacao.id,
        nome="Cliente",
        cpf="12345678901",
        telefone="11999999999",
    )
    db_session.add(cl)
    db_session.flush()
    m = Moto(operacao_id=operacao.id, placa="ABC1D23", modelo="Biz", status="alugada")
    db_session.add(m)
    db_session.flush()
    ct = Contrato(
        operacao_id=operacao.id,
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
        operacao_id=operacao.id,
        contrato_id=ct.id,
        valor=Decimal("100"),
        vencimento=date(2025, 2, 1),
        status=CobrancaStatus.PENDENTE.value,
    )
    db_session.add(cob)
    db_session.commit()
    return cob, cl


def test_pay_cobranca_approved(db_session, operacao_a, dono_user):
    cob, _ = _seed_cobranca(db_session, operacao=operacao_a)
    mp_result = MercadoPagoOrderResult(
        order_id="ORD-99",
        payment_id="PAY-99",
        order_status="processed",
        payment_status="processed",
        status_detail="accredited",
        pix_copia_cola=None,
        three_ds_info=None,
        requires_3ds=False,
    )
    with patch(
        "motopay.services.card_payment_service.MercadoPagoClient"
    ) as mock_cls:
        mock_cls.return_value.create_online_order.return_value = mp_result
        out = pay_cobranca_with_card(
            db_session,
            _dono_current(dono_user),
            None,
            cob.id,
            token="card-tok",
            payment_method_id="visa",
        )
    assert out.cobranca_finalizada is True
    assert out.payment_id == "PAY-99"
    assert cob.mercadopago_order_id == "ORD-99"
    db_session.refresh(cob)
    assert cob.status == CobrancaStatus.RECEBIDO.value


def test_pay_cobranca_pending_challenge(db_session, operacao_a, dono_user):
    cob, _ = _seed_cobranca(db_session, operacao=operacao_a)
    mp_result = MercadoPagoOrderResult(
        order_id="ORD-3ds",
        payment_id="PAY-3ds",
        order_status="action_required",
        payment_status="action_required",
        status_detail="pending_challenge",
        pix_copia_cola=None,
        three_ds_info=ThreeDsInfo(
            external_resource_url="https://mp.test/3ds",
            creq="creq",
        ),
        requires_3ds=True,
    )
    with patch(
        "motopay.services.card_payment_service.MercadoPagoClient"
    ) as mock_cls:
        mock_cls.return_value.create_online_order.return_value = mp_result
        out = pay_cobranca_with_card(
            db_session,
            _dono_current(dono_user),
            None,
            cob.id,
            token="card-tok",
        )
    assert out.requires_3ds is True
    assert out.three_ds_info is not None
    db_session.refresh(cob)
    assert cob.mercadopago_payment_id == "PAY-3ds"
    assert cob.mercadopago_order_id == "ORD-3ds"
    assert cob.status == CobrancaStatus.PENDENTE.value


def test_save_cliente_card_persists_row(db_session, operacao_a, dono_user):
    operacao_a.mercadopago_access_token = "tok"
    operacao_a.mercadopago_public_key = "pk"
    operacao_a.mercadopago_webhook_secret = "wh"
    cl = Cliente(
        operacao_id=operacao_a.id,
        nome="C",
        cpf="98765432100",
        telefone="11888888888",
    )
    db_session.add(cl)
    db_session.commit()

    with patch(
        "motopay.services.card_payment_service.MercadoPagoClient"
    ) as mock_cls:
        inst = mock_cls.return_value
        inst.ensure_customer.return_value = "cust-1"
        inst.save_card.return_value = {
            "id": "card-mp-1",
            "payment_method": {"id": "visa"},
            "last_four_digits": "4242",
            "cardholder": {"name": "TEST"},
            "expiration_month": 12,
            "expiration_year": 2030,
        }
        out = save_cliente_card(
            db_session, _dono_current(dono_user), None, cl.id, card_token="tok-save"
        )
    assert out.last_four_digits == "4242"
    db_session.refresh(cl)
    assert cl.mercadopago_customer_id == "cust-1"


def test_card_payment_api(client, db_session, operacao_a, dono_user, monkeypatch):
    monkeypatch.setenv("MERCADOPAGO_ACCESS_TOKEN", "global")
    monkeypatch.setenv("MERCADOPAGO_PUBLIC_KEY", "pk")
    monkeypatch.setenv("MERCADOPAGO_WEBHOOK_SECRET", "wh")
    from motopay.config import get_settings

    get_settings.cache_clear()
    cob, _ = _seed_cobranca(db_session, operacao=operacao_a)
    tokens = login(client, dono_user.email, "donodono")
    mp_result = MercadoPagoOrderResult(
        order_id="ORD-api",
        payment_id="PAY-api",
        order_status="action_required",
        payment_status="action_required",
        status_detail="pending_challenge",
        pix_copia_cola=None,
        three_ds_info=ThreeDsInfo("https://x", "c"),
        requires_3ds=True,
    )
    with (
        patch(
            "motopay.services.card_payment_service.MercadoPagoClient"
        ) as mock_cls,
        patch("motopay.interfaces.api.routers.cobrancas.handle_domain_event") as mock_task,
    ):
        mock_cls.return_value.create_online_order.return_value = mp_result
        mock_task.delay = MagicMock()
        r = client.post(
            f"/api/v1/cobrancas/{cob.id}/card-payment",
            headers=auth_header(tokens["access_token"]),
            json={"token": "t", "installments": 1, "payment_method_id": "visa"},
        )
    assert r.status_code == 200
    data = r.json()
    assert data["requires_3ds"] is True
    assert data["payment_id"] == "PAY-api"
    get_settings.cache_clear()
