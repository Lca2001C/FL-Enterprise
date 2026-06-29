"""Testes de integração do bot Telegram: menu, contato e notificação ao dono."""

from __future__ import annotations

from unittest.mock import patch

from motopay.domain.enums import UserRole
from motopay.infrastructure.db.models import Cliente
from motopay.infrastructure.telegram.bot_main import _notify_owner_contact
from motopay.infrastructure.telegram.conversation import (
    detect_intent,
    is_contact_request,
    is_menu_request,
)
from motopay.infrastructure.telegram.templates import (
    DEFAULT_BOT_MENU_BUTTONS,
    DEFAULT_BOT_MENU_CONTACT_BUTTON,
    match_button_command,
    render_menu_button_response,
    resolve_bot_menu_buttons,
    validate_bot_menu_buttons,
)
from motopay.interfaces.api.schemas import OperacaoUpdate, TelegramBotMenuButton
from motopay.services.operacao_service import update_operacao

from tests.conftest import auth_header, login


def test_default_menu_passes_validation() -> None:
    validated = validate_bot_menu_buttons([dict(b) for b in DEFAULT_BOT_MENU_BUTTONS])
    assert len(validated) == 4
    assert validated[-1]["command"] == "contato"


def test_default_contato_button_matches_label() -> None:
    cmd = match_button_command("📞 Falar com Atendente", DEFAULT_BOT_MENU_BUTTONS)
    assert cmd == "contato"


def test_default_contato_button_renders_response() -> None:
    text = render_menu_button_response(
        DEFAULT_BOT_MENU_CONTACT_BUTTON,
        menu_ctx={
            "cliente": "Carlos",
            "proximo_vencimento": "2026-06-01",
            "placa": "XYZ9K88",
            "inadimplente": "não",
            "promessa_pagamento_em": "—",
        },
    )
    assert "Carlos" in text
    assert "contato em breve" in text.lower()


def test_contact_label_detected_as_contact_intent() -> None:
    assert detect_intent("Quero falar com alguém") == "contact"
    assert is_contact_request(
        "Quero falar com alguém",
        button=DEFAULT_BOT_MENU_CONTACT_BUTTON,
    )


def test_menu_and_payment_are_not_contact() -> None:
    assert is_menu_request("menu") is True
    assert is_contact_request("menu") is False
    assert is_contact_request("Qual o pix para pagar?") is False
    assert detect_intent("Qual o pix para pagar?") == "payment"


def test_bot_notify_owner_on_contact_message(db_session, operacao_a) -> None:
    operacao_a.telegram_owner_notify_enabled = True
    operacao_a.telegram_owner_notify_id = "777888999"
    db_session.add(operacao_a)
    db_session.flush()
    cliente = Cliente(
        operacao_id=operacao_a.id,
        nome="Ana Costa",
        cpf="11122233344",
        telefone="(21) 98888-7777",
        telegram_id="123456789",
        score=100,
    )
    db_session.add(cliente)
    db_session.flush()
    menu_ctx = {
        "cliente": cliente.nome,
        "proximo_vencimento": "2026-07-01",
        "placa": "ABC1D23",
        "inadimplente": "não",
        "promessa_pagamento_em": "—",
    }
    with patch("motopay.infrastructure.telegram.owner_notify.send_telegram_text") as send_mock:
        _notify_owner_contact(
            db_session,
            cliente=cliente,
            uid="123456789",
            user_message="📞 Falar com Atendente",
            menu_ctx=menu_ctx,
            button=DEFAULT_BOT_MENU_CONTACT_BUTTON,
        )
        send_mock.assert_called_once()
        body = send_mock.call_args.kwargs["text"]
        assert "Ana Costa" in body
        assert "(21) 98888-7777" in body
        assert "📞 Falar com Atendente" in body


def test_bot_notifies_owner_without_cliente_on_contact(db_session, operacao_a) -> None:
    operacao_a.telegram_owner_notify_enabled = True
    operacao_a.telegram_owner_notify_id = "777888999"
    db_session.add(operacao_a)
    db_session.commit()
    with patch("motopay.infrastructure.telegram.owner_notify.send_telegram_text") as send_mock:
        _notify_owner_contact(
            db_session,
            cliente=None,
            uid="999",
            user_message="Quero falar com alguém",
            menu_ctx={"cliente": "visitante"},
        )
        send_mock.assert_called_once()
        assert send_mock.call_args.kwargs["chat_id"] == "777888999"


def test_save_default_menu_with_contato_via_service(db_session, operacao_a) -> None:
    buttons = [TelegramBotMenuButton.model_validate(b) for b in DEFAULT_BOT_MENU_BUTTONS]
    out = update_operacao(
        db_session,
        operacao_a.id,
        OperacaoUpdate(telegram_bot_menu_buttons=buttons),
        role=UserRole.DONO,
    )
    assert len(out.telegram_bot_menu_buttons) == 4
    contato = next(b for b in out.telegram_bot_menu_buttons if b.command == "contato")
    assert contato.label == "📞 Falar com Atendente"
    assert contato.response is not None


def test_resolve_saved_menu_from_db(db_session, operacao_a) -> None:
    operacao_a.telegram_bot_menu_buttons = [dict(b) for b in DEFAULT_BOT_MENU_BUTTONS]
    db_session.add(operacao_a)
    db_session.commit()
    resolved = resolve_bot_menu_buttons(operacao_a.telegram_bot_menu_buttons)
    assert match_button_command("📞 Falar com Atendente", resolved) == "contato"


def test_api_dono_me_returns_default_contato_button(client, dono_user) -> None:
    tokens = login(client, "dono@test.local", "donodono")
    response = client.get("/api/v1/operacoes/me", headers=auth_header(tokens["access_token"]))
    assert response.status_code == 200
    data = response.json()
    commands = [b["command"] for b in data["telegram_bot_menu_buttons"]]
    assert "contato" in commands


def test_api_dono_can_enable_owner_notify(client, dono_user) -> None:
    tokens = login(client, "dono@test.local", "donodono")
    response = client.patch(
        "/api/v1/operacoes/me",
        headers=auth_header(tokens["access_token"]),
        json={
            "telegram_owner_notify_enabled": True,
            "telegram_owner_notify_id": "1122334455",
            "telegram_bot_menu_buttons": [dict(b) for b in DEFAULT_BOT_MENU_BUTTONS],
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["telegram_owner_notify_enabled"] is True
    assert data["telegram_owner_notify_id"] == "1122334455"
    assert any(b["command"] == "contato" for b in data["telegram_bot_menu_buttons"])


def test_api_dono_full_telegram_config_roundtrip(client, dono_user) -> None:
    tokens = login(client, "dono@test.local", "donodono")
    patch_body = {
        "telegram_owner_notify_enabled": True,
        "telegram_owner_notify_id": "9988776655",
        "telegram_bot_menu_buttons": [dict(b) for b in DEFAULT_BOT_MENU_BUTTONS],
        "telegram_templates": {"bot_chat_contact": "Custom contact reply for {cliente}."},
    }
    patch = client.patch(
        "/api/v1/operacoes/me",
        headers=auth_header(tokens["access_token"]),
        json=patch_body,
    )
    assert patch.status_code == 200, patch.text

    get = client.get("/api/v1/operacoes/me", headers=auth_header(tokens["access_token"]))
    assert get.status_code == 200
    data = get.json()
    assert data["telegram_owner_notify_enabled"] is True
    assert data["telegram_owner_notify_id"] == "9988776655"
    assert data["telegram_templates"]["bot_chat_contact"] == "Custom contact reply for {cliente}."
    contato = next(b for b in data["telegram_bot_menu_buttons"] if b["command"] == "contato")
    assert contato["label"] == "📞 Falar com Atendente"
