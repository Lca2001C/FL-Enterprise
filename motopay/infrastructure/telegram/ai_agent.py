from __future__ import annotations

import logging
from typing import Any

import httpx

from motopay.config import get_settings

logger = logging.getLogger(__name__)


def ai_reply(
    *,
    user_message: str,
    context: dict[str, Any],
    history: list[dict[str, str]] | None = None,
) -> str | None:
    """Resposta opcional via OpenAI. Retorna None se desligado ou falhar."""
    settings = get_settings()
    if not settings.ai_bot_enabled or not settings.openai_api_key.strip():
        return None
    system = (
        "Você é assistente do MotoPay (locação de motos). "
        "Responda em português, de forma breve, empática e objetiva (1-3 frases). "
        "Não repita o menu inteiro nem liste todos os comandos a cada mensagem. "
        "Se o cliente pedir humano ou tiver dúvida complexa, diga que a equipe entrará em contato em breve. "
        "Para Pix ou status, sugira os botões do teclado ou /pix e /status. "
        f"Contexto do cliente: {context}"
    )
    messages: list[dict[str, str]] = [{"role": "system", "content": system}]
    if history:
        messages.extend(history)
    else:
        messages.append({"role": "user", "content": user_message})
    if history:
        messages.append({"role": "user", "content": user_message})
    payload = {
        "model": "gpt-4o-mini",
        "messages": messages,
        "max_tokens": 300,
    }
    try:
        r = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30.0,
        )
        r.raise_for_status()
        data = r.json()
        return str(data["choices"][0]["message"]["content"]).strip()
    except Exception as exc:
        logger.exception("ai_bot_reply_failed: %s", exc)
        return None
