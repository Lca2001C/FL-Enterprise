from __future__ import annotations

import logging
from typing import Any

import httpx

from motopay.config import get_settings

logger = logging.getLogger(__name__)


def ai_reply(*, user_message: str, context: dict[str, Any]) -> str | None:
    """Resposta opcional via OpenAI. Retorna None se desligado ou falhar."""
    settings = get_settings()
    if not settings.ai_bot_enabled or not settings.openai_api_key.strip():
        return None
    system = (
        "Você é assistente do MotoPay (locação de motos). "
        "Responda em português, de forma breve e objetiva. "
        f"Contexto do cliente: {context}"
    )
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_message},
        ],
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
