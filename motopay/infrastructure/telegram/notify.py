from __future__ import annotations

import httpx

from motopay.config import get_settings
from motopay.infrastructure.messaging.celery_observability import telegram_safe_call
from motopay.observability.logger import get_logger
from motopay.observability.metrics import (
    telegram_messages_failed,
    telegram_messages_sent,
    telegram_rate_limit_hits,
)

logger = get_logger(__name__)


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


def _classify_telegram_json_fail(data: dict, r: httpx.Response) -> TelegramNotifyError:
    desc = str(data.get("description", "Telegram API error"))
    err_code = data.get("error_code")

    t = _transient_from_http(r, desc)
    if t is not None:
        return t
    if err_code == 429:
        telegram_rate_limit_hits.inc()
        return TelegramTransientError(desc)
    logger.warning(
        "telegram_send_permanent_failure error_code=%s desc=%s http_status=%s",
        err_code,
        desc,
        r.status_code,
    )
    return TelegramPermanentError(desc)


def _send_impl(*, chat_id: str, payload: dict, tenant_id: str = "global") -> None:
    token = get_settings().telegram_bot_token
    if not token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        r = httpx.post(url, json={"chat_id": chat_id, **payload}, timeout=30.0)
    except httpx.TimeoutException as e:
        telegram_messages_failed.labels(tenant_id=tenant_id).inc()
        raise TelegramTransientError("Telegram request timeout") from e
    except httpx.ConnectError as e:
        telegram_messages_failed.labels(tenant_id=tenant_id).inc()
        raise TelegramTransientError("Telegram connection error") from e
    except httpx.RequestError as e:
        telegram_messages_failed.labels(tenant_id=tenant_id).inc()
        raise TelegramTransientError(f"Telegram request error: {e}") from e

    try:
        data = r.json()
    except ValueError as e:
        t = _transient_from_http(r, r.text[:200])
        telegram_messages_failed.labels(tenant_id=tenant_id).inc()
        if t is not None:
            raise t from e
        raise TelegramPermanentError("Resposta não-JSON do Telegram") from e

    if not isinstance(data, dict):
        telegram_messages_failed.labels(tenant_id=tenant_id).inc()
        raise TelegramPermanentError("Resposta inesperada do Telegram")

    if data.get("ok") is True:
        telegram_messages_sent.labels(tenant_id=tenant_id).inc()
        return

    telegram_messages_failed.labels(tenant_id=tenant_id).inc()
    if not r.is_success:
        t = _transient_from_http(r, str(data.get("description", r.text)))
        if t is not None:
            raise t
    raise _classify_telegram_json_fail(data, r)


@telegram_safe_call
def send_telegram_text(*, chat_id: str, text: str) -> None:
    _send_impl(chat_id=chat_id, payload={"text": text})


@telegram_safe_call
def send_telegram_html(*, chat_id: str, html: str) -> None:
    _send_impl(chat_id=chat_id, payload={"text": html, "parse_mode": "HTML"})
