from __future__ import annotations

import httpx

from motopay.config import get_settings


def send_telegram_text(*, chat_id: str, text: str) -> None:
    token = get_settings().telegram_bot_token
    if not token or not chat_id:
        return
    httpx.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text},
        timeout=30.0,
    )
