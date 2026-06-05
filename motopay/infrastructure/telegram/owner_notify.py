"""Notifica o dono da operação no Telegram sobre pedidos de contato."""

from __future__ import annotations

from motopay.infrastructure.db.models import Cliente, Operacao
from motopay.infrastructure.telegram.notify import TelegramPermanentError, send_telegram_text
from motopay.observability.logger import get_logger

logger = get_logger(__name__)


def build_owner_contact_notify_text(
    *,
    operacao_nome: str,
    cliente: Cliente | None,
    telegram_user_id: str,
    user_message: str,
    menu_ctx: dict[str, str],
) -> str:
    nome = cliente.nome if cliente else menu_ctx.get("cliente", "visitante")
    telefone = cliente.telefone if cliente else "—"
    lines = [
        "📩 Pedido de contato — MotoPay",
        f"Operação: {operacao_nome}",
        "",
        f"Cliente: {nome}",
        f"Telefone: {telefone}",
        f"Telegram ID: {telegram_user_id}",
    ]
    placa = menu_ctx.get("placa")
    if placa and placa != "—":
        lines.append(f"Placa: {placa}")
    inadimplente = menu_ctx.get("inadimplente")
    if inadimplente and inadimplente != "—":
        lines.append(f"Inadimplente: {inadimplente}")
    lines.extend(["", f"Mensagem: {user_message.strip()}"])
    return "\n".join(lines)


def notify_owner_contact_request(
    *,
    operacao: Operacao,
    cliente: Cliente | None,
    telegram_user_id: str,
    user_message: str,
    menu_ctx: dict[str, str],
) -> None:
    if not operacao.telegram_owner_notify_enabled:
        return
    chat_id = (operacao.telegram_owner_notify_id or "").strip()
    if not chat_id:
        return
    text = build_owner_contact_notify_text(
        operacao_nome=operacao.nome,
        cliente=cliente,
        telegram_user_id=telegram_user_id,
        user_message=user_message,
        menu_ctx=menu_ctx,
    )
    try:
        send_telegram_text(chat_id=chat_id, text=text)
    except TelegramPermanentError as exc:
        logger.warning(
            "owner_contact_notify_skipped operacao_id=%s chat_id=%s: %s",
            operacao.id,
            chat_id,
            exc,
        )
    except Exception as exc:
        logger.warning(
            "owner_contact_notify_failed operacao_id=%s: %s",
            operacao.id,
            exc,
        )


def notify_owner_refund(
    *,
    operacao: Operacao,
    cobranca_id: int,
    delta: str,
    payment_id: str,
) -> None:
    if not operacao.telegram_owner_notify_enabled:
        return
    chat_id = (operacao.telegram_owner_notify_id or "").strip()
    if not chat_id:
        return
    text = (
        "Estorno Mercado Pago\n"
        f"Operação: {operacao.nome}\n"
        f"Cobrança #{cobranca_id}\n"
        f"Valor estornado: R$ {delta}\n"
        f"Payment ID: {payment_id}"
    )
    try:
        send_telegram_text(chat_id=chat_id, text=text)
    except Exception as exc:
        logger.warning("owner_refund_notify_failed operacao_id=%s: %s", operacao.id, exc)


def notify_owner_chargeback(
    *,
    operacao: Operacao,
    cobranca_id: int,
    status: str,
    payment_id: str,
) -> None:
    if not operacao.telegram_owner_notify_enabled:
        return
    chat_id = (operacao.telegram_owner_notify_id or "").strip()
    if not chat_id:
        return
    text = (
        "Chargeback / disputa Mercado Pago\n"
        f"Operação: {operacao.nome}\n"
        f"Cobrança #{cobranca_id}\n"
        f"Status: {status}\n"
        f"Payment ID: {payment_id}\n"
        "Acompanhe no painel MP: https://www.mercadopago.com.br/activities/chargebacks"
    )
    try:
        send_telegram_text(chat_id=chat_id, text=text)
    except Exception as exc:
        logger.warning("owner_chargeback_notify_failed operacao_id=%s: %s", operacao.id, exc)
