"""Classificação de mensagens livres e respostas contextuais do bot."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from motopay.infrastructure.telegram.templates import render_template

MAX_HISTORY = 8

_MENU_KEYWORDS = frozenset(
    {
        "menu",
        "opcoes",
        "opções",
        "inicio",
        "início",
        "start",
        "comandos",
        "ajuda menu",
    }
)

_GREETING_RE = re.compile(
    r"^(oi|olá|ola|bom dia|boa tarde|boa noite|hey|e aí|e ai|salve)\b",
    re.IGNORECASE,
)
_THANKS_RE = re.compile(
    r"\b(obrigad[oa]|valeu|agradeço|agradeco|brigad[ao]|thanks)\b",
    re.IGNORECASE,
)
_CONTACT_RE = re.compile(
    r"\b(atendente|operador|humano|falar com|contato|ligar|whatsapp|suporte|"
    r"alguém|alguem|equipe|retorno|retornar)\b",
    re.IGNORECASE,
)
_PAYMENT_RE = re.compile(
    r"\b(pix|pagar|pagamento|boleto|vencimento|atraso|atrasad[oa]|"
    r"inadimpl|débito|debito|valor|quanto devo)\b",
    re.IGNORECASE,
)


def _normalize(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text.strip().lower())
    return "".join(c for c in folded if not unicodedata.combining(c))


def is_menu_request(text: str) -> bool:
    norm = _normalize(text)
    if norm in _MENU_KEYWORDS:
        return True
    return norm.startswith("menu ") or norm.startswith("/start")


def detect_intent(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return "general"
    if _GREETING_RE.match(stripped) and len(stripped.split()) <= 4:
        return "greeting"
    if _THANKS_RE.search(stripped):
        return "thanks"
    if _CONTACT_RE.search(stripped):
        return "contact"
    if _PAYMENT_RE.search(stripped):
        return "payment"
    return "general"


_CONTACT_COMMAND_SLUGS = frozenset(
    {"contato", "atendimento", "atendente", "falar", "suporte", "humano", "operador"}
)


def is_contact_request(text: str, *, button: dict[str, str] | None = None) -> bool:
    if detect_intent(text) == "contact":
        return True
    if button:
        command = str(button.get("command", "")).strip().lower()
        if command in _CONTACT_COMMAND_SLUGS:
            return True
        label = str(button.get("label", "")).strip()
        if label and _CONTACT_RE.search(label):
            return True
    return False


def template_key_for_intent(intent: str) -> str:
    return {
        "greeting": "bot_chat_greeting",
        "thanks": "bot_chat_thanks",
        "contact": "bot_chat_contact",
        "payment": "bot_chat_payment",
    }.get(intent, "bot_chat_ack")


def append_history(history: list[dict[str, str]], role: str, content: str) -> list[dict[str, str]]:
    updated = [*history, {"role": role, "content": content}]
    return updated[-MAX_HISTORY:]


def contextual_reply_text(
    *,
    user_message: str,
    overrides: dict[str, str] | None,
    menu_ctx: dict[str, str],
    intent: str | None = None,
) -> str:
    key = template_key_for_intent(intent or detect_intent(user_message))
    return render_template(key, overrides=overrides, **menu_ctx)


def ai_context_from_menu(menu_ctx: dict[str, str], *, user_message: str) -> dict[str, Any]:
    return {
        **menu_ctx,
        "ultima_mensagem": user_message,
        "intencao": detect_intent(user_message),
    }
