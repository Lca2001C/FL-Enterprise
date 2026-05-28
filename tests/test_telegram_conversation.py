from __future__ import annotations

from motopay.infrastructure.telegram.conversation import (
    contextual_reply_text,
    detect_intent,
    is_contact_request,
    is_menu_request,
    template_key_for_intent,
)


def test_is_menu_request() -> None:
    assert is_menu_request("menu") is True
    assert is_menu_request("opções") is True
    assert is_menu_request("oi") is False


def test_detect_intent_greeting() -> None:
    assert detect_intent("Oi") == "greeting"
    assert detect_intent("Bom dia") == "greeting"


def test_detect_intent_thanks() -> None:
    assert detect_intent("Muito obrigado!") == "thanks"


def test_detect_intent_contact() -> None:
    assert detect_intent("Quero falar com um atendente") == "contact"


def test_is_contact_request() -> None:
    assert is_contact_request("Quero falar com alguém") is True
    assert is_contact_request("obrigado") is False


def test_detect_intent_payment() -> None:
    assert detect_intent("Qual o pix para pagar?") == "payment"


def test_detect_intent_general() -> None:
    assert detect_intent("Minha moto quebrou ontem") == "general"


def test_template_key_for_intent() -> None:
    assert template_key_for_intent("contact") == "bot_chat_contact"


def test_contextual_reply_text_uses_template() -> None:
    text = contextual_reply_text(
        user_message="preciso de ajuda",
        overrides=None,
        menu_ctx={"cliente": "Maria"},
        intent="general",
    )
    assert "Maria" in text
    assert "contato" in text.lower()
