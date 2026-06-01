from __future__ import annotations

from unittest.mock import patch

from motopay.domain.enums import UserRole
from motopay.infrastructure.db.models import Cliente
from motopay.infrastructure.telegram.conversation import is_contact_request
from motopay.infrastructure.telegram.owner_notify import (
    build_owner_contact_notify_text,
    notify_owner_contact_request,
)
from motopay.interfaces.api.schemas import OperacaoUpdate
from motopay.services.operacao_service import update_operacao


def test_is_contact_request_from_text() -> None:
    assert is_contact_request("Quero falar com alguém") is True
    assert is_contact_request("oi") is False


def test_is_contact_request_from_button_slug() -> None:
    btn = {"label": "Contato", "command": "contato", "response": "Ok"}
    assert is_contact_request("Contato", button=btn) is True


def test_is_contact_request_from_button_label() -> None:
    btn = {"label": "Falar com operador", "command": "info", "response": "Ok"}
    assert is_contact_request("Falar com operador", button=btn) is True


def test_build_owner_contact_notify_text() -> None:
    cliente = Cliente(
        id=1,
        operacao_id=1,
        nome="Maria",
        cpf="000",
        telefone="(11) 99999-9999",
        telegram_id="123",
        score=100,
    )
    text = build_owner_contact_notify_text(
        operacao_nome="Centro",
        cliente=cliente,
        telegram_user_id="123456789",
        user_message="Preciso de ajuda",
        menu_ctx={"cliente": "Maria", "placa": "ABC1D23", "inadimplente": "não"},
    )
    assert "Maria" in text
    assert "(11) 99999-9999" in text
    assert "Preciso de ajuda" in text
    assert "ABC1D23" in text


def test_notify_owner_skips_when_disabled(db_session, operacao_a) -> None:
    operacao_a.telegram_owner_notify_enabled = False
    operacao_a.telegram_owner_notify_id = "999"
    db_session.add(operacao_a)
    db_session.commit()
    with patch("motopay.infrastructure.telegram.owner_notify.send_telegram_text") as send_mock:
        notify_owner_contact_request(
            operacao=operacao_a,
            cliente=None,
            telegram_user_id="111",
            user_message="Quero atendente",
            menu_ctx={"cliente": "João"},
        )
        send_mock.assert_not_called()


def test_notify_owner_sends_when_enabled(db_session, operacao_a) -> None:
    operacao_a.telegram_owner_notify_enabled = True
    operacao_a.telegram_owner_notify_id = "888777666"
    db_session.add(operacao_a)
    db_session.commit()
    with patch("motopay.infrastructure.telegram.owner_notify.send_telegram_text") as send_mock:
        notify_owner_contact_request(
            operacao=operacao_a,
            cliente=None,
            telegram_user_id="111",
            user_message="Quero atendente",
            menu_ctx={"cliente": "João"},
        )
        send_mock.assert_called_once()
        assert send_mock.call_args.kwargs["chat_id"] == "888777666"


def test_dono_can_save_owner_notify_settings(db_session, operacao_a) -> None:
    out = update_operacao(
        db_session,
        operacao_a.id,
        OperacaoUpdate(
            telegram_owner_notify_enabled=True,
            telegram_owner_notify_id="123456789",
        ),
        role=UserRole.DONO,
    )
    assert out.telegram_owner_notify_enabled is True
    assert out.telegram_owner_notify_id == "123456789"
    db_session.refresh(operacao_a)
    assert operacao_a.telegram_owner_notify_id == "123456789"
