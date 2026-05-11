from __future__ import annotations

import logging
from typing import Any

import httpx

from motopay.config import get_settings

logger = logging.getLogger(__name__)


class TelegramNotifyError(Exception):
    """Falha ao enviar mensagem via Bot API."""


class TelegramTransientError(TelegramNotifyError):
    """Erro transitório (rede, 5xx, flood). Vale retry no Celery."""


class TelegramPermanentError(TelegramNotifyError):
    """Erro permanente (chat inválido, bot bloqueado). Não retry."""


def _transient_from_http(r: httpx.Response, desc: str) -> TelegramTransientError | None:
    if r.status_code >= 500 or r.status_code == 429:
        return TelegramTransientError(f"HTTP {r.status_code}: {desc}")
    return None


def _classify_telegram_json_fail(data: dict[str, Any], r: httpx.Response) -> TelegramNotifyError:
    desc = str(data.get("description", "Telegram API error"))
    err_code = data.get("error_code")

    t = _transient_from_http(r, desc)
    if t is not None:
        return t
    if err_code == 429:
        return TelegramTransientError(desc)
    # 5xx-only path already handled; Telegram costuma responder 200 com ok:false
    logger.warning(
        "telegram_send_permanent_failure error_code=%s desc=%s http_status=%s",
        err_code,
        desc,
        r.status_code,
    )
    return TelegramPermanentError(desc)


def send_telegram_text(*, chat_id: str, text: str) -> None:
    token = get_settings().telegram_bot_token
    if not token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        r = httpx.post(url, json={"chat_id": chat_id, "text": text}, timeout=30.0)
    except httpx.TimeoutException as e:
        raise TelegramTransientError("Telegram request timeout") from e
    except httpx.ConnectError as e:
        raise TelegramTransientError("Telegram connection error") from e
    except httpx.RequestError as e:
        raise TelegramTransientError(f"Telegram request error: {e}") from e

    try:
        data = r.json()
    except ValueError as e:
        t = _transient_from_http(r, r.text[:200])
        if t is not None:
            raise t from e
        raise TelegramPermanentError("Resposta não-JSON do Telegram") from e

    if not isinstance(data, dict):
        raise TelegramPermanentError("Resposta inesperada do Telegram")

    if data.get("ok") is True:
        return

    if not r.is_success:
        t = _transient_from_http(r, str(data.get("description", r.text)))
        if t is not None:
            raise t
    raise _classify_telegram_json_fail(data, r)
