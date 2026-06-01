from __future__ import annotations

import pytest
from motopay.domain.enums import UserRole
from motopay.domain.exceptions import ConflictError
from motopay.infrastructure.telegram.templates import (
    DEFAULT_BOT_MENU_BUTTONS,
    DEFAULT_TELEGRAM_TEMPLATES,
    find_menu_button_by_command,
    match_button_command,
    render_menu_button_response,
    render_template,
    resolve_bot_menu_buttons,
    validate_bot_menu_buttons,
)
from motopay.interfaces.api.schemas import OperacaoUpdate, TelegramBotMenuButton
from motopay.services.operacao_service import operacao_to_out, update_operacao


def test_resolve_bot_menu_buttons_uses_defaults_when_null() -> None:
    buttons = resolve_bot_menu_buttons(None)
    assert buttons == DEFAULT_BOT_MENU_BUTTONS
    assert any(b["command"] == "contato" for b in buttons)


def test_default_menu_includes_contato_button() -> None:
    contato = next(b for b in DEFAULT_BOT_MENU_BUTTONS if b["command"] == "contato")
    assert contato["label"] == "Quero falar com alguém"
    assert "{cliente}" in contato["response"]


def test_validate_bot_menu_buttons_rejects_invalid_command() -> None:
    with pytest.raises(ConflictError, match="Comando personalizado"):
        validate_bot_menu_buttons([{"label": "Foo", "command": "invalid"}])


def test_validate_bot_menu_buttons_accepts_menu_command() -> None:
    buttons = validate_bot_menu_buttons([{"label": "Menu", "command": "menu"}])
    assert buttons[0]["command"] == "menu"


def test_validate_bot_menu_buttons_accepts_custom_command() -> None:
    buttons = validate_bot_menu_buttons(
        [
            {
                "label": "Horário",
                "command": "horario",
                "response": "Atendemos das 8h às 18h, {cliente}.",
            }
        ]
    )
    assert buttons[0]["command"] == "horario"
    assert "8h" in buttons[0]["response"]


def test_validate_bot_menu_buttons_rejects_custom_without_response() -> None:
    with pytest.raises(ConflictError, match="precisa de uma resposta"):
        validate_bot_menu_buttons([{"label": "Horário", "command": "horario"}])


def test_find_menu_button_by_command() -> None:
    buttons = [{"label": "Contato", "command": "contato", "response": "Ok"}]
    assert find_menu_button_by_command("contato", buttons) == buttons[0]
    assert find_menu_button_by_command("outro", buttons) is None


def test_render_menu_button_response() -> None:
    btn = {"label": "Contato", "command": "contato", "response": "Olá, {cliente}!"}
    text = render_menu_button_response(btn, menu_ctx={"cliente": "Ana", "placa": "—"})
    assert text == "Olá, Ana!"


def test_validate_bot_menu_buttons_rejects_duplicate_labels() -> None:
    with pytest.raises(ConflictError, match="duplicado"):
        validate_bot_menu_buttons(
            [
                {"label": "Status", "command": "status"},
                {"label": "Status", "command": "pix"},
            ]
        )


def test_validate_bot_menu_buttons_rejects_empty_list() -> None:
    with pytest.raises(ConflictError, match="pelo menos um"):
        validate_bot_menu_buttons([])


def test_match_button_command_finds_label() -> None:
    buttons = [{"label": "Pix", "command": "pix"}]
    assert match_button_command("Pix", buttons) == "pix"
    assert match_button_command("  Pix  ", buttons) == "pix"
    assert match_button_command("Outro", buttons) is None


def test_render_bot_start_with_context() -> None:
    text = render_template(
        "bot_start",
        cliente="Maria",
        proximo_vencimento="2026-06-01",
        placa="XYZ9K88",
        inadimplente="não",
        promessa_pagamento_em="—",
    )
    assert "Maria" in text
    assert "XYZ9K88" in text
    assert "2026-06-01" in text


def test_operacao_to_out_includes_default_menu_buttons(db_session, operacao_a) -> None:
    out = operacao_to_out(operacao_a)
    assert len(out.telegram_bot_menu_buttons) == 4
    assert out.telegram_bot_menu_buttons[0].command == "status"
    assert any(b.command == "contato" for b in out.telegram_bot_menu_buttons)


def test_dono_can_save_menu_buttons(db_session, operacao_a) -> None:
    custom = [
        TelegramBotMenuButton(label="Meu Pix", command="pix"),
        TelegramBotMenuButton(label="Situação", command="status"),
    ]
    out = update_operacao(
        db_session,
        operacao_a.id,
        OperacaoUpdate(telegram_bot_menu_buttons=custom),
        role=UserRole.DONO,
    )
    assert len(out.telegram_bot_menu_buttons) == 2
    assert out.telegram_bot_menu_buttons[0].label == "Meu Pix"
    db_session.refresh(operacao_a)
    assert operacao_a.telegram_bot_menu_buttons[0]["label"] == "Meu Pix"


def test_bot_start_default_has_placeholders() -> None:
    text = DEFAULT_TELEGRAM_TEMPLATES["bot_start"]
    assert "{cliente}" in text
    assert "{placa}" in text
