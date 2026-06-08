"""Telegram bot (polling). Comandos: /start, /menu, /promessa, /pix, /status, /ajuda."""

from __future__ import annotations

import io as _io
from datetime import date

try:
    import qrcode as _qrcode  # type: ignore[import]
    _QR_AVAILABLE = True
except ImportError:
    _QR_AVAILABLE = False

from sqlalchemy import select
from telegram import KeyboardButton, ReplyKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from motopay.config import get_settings
from motopay.domain.enums import ContratoStatus
from motopay.infrastructure.db.models import Cliente, Contrato, Moto, Operacao
from motopay.infrastructure.db.session import SessionLocal
from motopay.infrastructure.telegram.ai_agent import ai_reply
from motopay.infrastructure.telegram.conversation import (
    ai_context_from_menu,
    append_history,
    contextual_reply_text,
    detect_intent,
    is_contact_request,
    is_menu_request,
)
from motopay.infrastructure.telegram.owner_notify import notify_owner_contact_request
from motopay.infrastructure.telegram.templates import (
    find_menu_button_by_command,
    format_brl,
    match_button_command,
    render_menu_button_response,
    render_template,
    resolve_bot_menu_buttons,
)
from motopay.services.billing_service import charge_amounts_for_cobranca, get_open_cobranca
from motopay.services.payer_portal_service import ensure_portal_url_for_cobranca
from motopay.services.negotiation_service import record_promessa_from_telegram_user


def _make_pix_qr_bytes(pix_code: str) -> bytes | None:
    """Gera QR code PNG a partir do código Pix. Retorna None se qrcode não instalado."""
    if not _QR_AVAILABLE:
        return None
    qr = _qrcode.QRCode(
        error_correction=_qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=4,
    )
    qr.add_data(pix_code)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = _io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _cliente_for_telegram(
    db, telegram_user_id: str
) -> tuple[Cliente | None, dict[str, str] | None, list[dict[str, str]]]:
    cliente = db.scalars(select(Cliente).where(Cliente.telegram_id == telegram_user_id)).first()
    overrides: dict[str, str] | None = None
    buttons = resolve_bot_menu_buttons(None)
    if cliente:
        op = db.get(Operacao, cliente.operacao_id)
        if op:
            overrides = op.telegram_templates
            buttons = resolve_bot_menu_buttons(op.telegram_bot_menu_buttons)
    return cliente, overrides, buttons


def _active_contrato(db, cliente_id: int) -> Contrato | None:
    return db.scalars(
        select(Contrato)
        .where(Contrato.cliente_id == cliente_id, Contrato.status == ContratoStatus.ATIVO.value)
        .order_by(Contrato.id.desc())
    ).first()


def _menu_context(db, cliente: Cliente | None, contrato: Contrato | None) -> dict[str, str]:
    if not cliente:
        return {
            "cliente": "visitante",
            "proximo_vencimento": "—",
            "placa": "—",
            "inadimplente": "—",
            "promessa_pagamento_em": "—",
        }
    placa = "—"
    if contrato:
        moto = db.get(Moto, contrato.moto_id)
        if moto:
            placa = moto.placa
    promessa = "—"
    proximo = "—"
    inadimplente = "—"
    if contrato:
        proximo = contrato.proximo_vencimento.isoformat()
        inadimplente = "sim" if contrato.inadimplente else "não"
        if contrato.promessa_pagamento_em:
            promessa = contrato.promessa_pagamento_em.isoformat()
    return {
        "cliente": cliente.nome,
        "proximo_vencimento": proximo,
        "placa": placa,
        "inadimplente": inadimplente,
        "promessa_pagamento_em": promessa,
    }


def _build_reply_keyboard(buttons: list[dict[str, str]]) -> ReplyKeyboardMarkup:
    row: list[KeyboardButton] = []
    rows: list[list[KeyboardButton]] = []
    for btn in buttons:
        row.append(KeyboardButton(btn["label"]))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def _find_menu_button_by_label(text: str, buttons: list[dict[str, str]]) -> dict[str, str] | None:
    stripped = text.strip()
    for btn in buttons:
        if stripped == btn["label"]:
            return btn
    return None


def _notify_owner_contact(
    db,
    *,
    cliente: Cliente | None,
    uid: str,
    user_message: str,
    menu_ctx: dict[str, str],
    button: dict[str, str] | None = None,
) -> None:
    if not is_contact_request(user_message, button=button):
        return
    if not cliente:
        return
    operacao = db.get(Operacao, cliente.operacao_id)
    if not operacao:
        return
    notify_owner_contact_request(
        operacao=operacao,
        cliente=cliente,
        telegram_user_id=uid,
        user_message=user_message,
        menu_ctx=menu_ctx,
    )


def _resolve_user_state(
    db, uid: str
) -> tuple[
    Cliente | None,
    dict[str, str] | None,
    list[dict[str, str]],
    dict[str, str],
    dict,
]:
    cliente, overrides, buttons = _cliente_for_telegram(db, uid) if uid else (None, None, resolve_bot_menu_buttons(None))
    if not uid:
        menu_ctx = _menu_context(None, None, None)
        return None, None, buttons, menu_ctx, {}
    contrato = _active_contrato(db, cliente.id) if cliente else None
    menu_ctx = _menu_context(db, cliente, contrato)
    ai_ctx: dict = menu_ctx.copy()
    if cliente:
        ai_ctx["score"] = cliente.score
        if contrato:
            ai_ctx["inadimplente_bool"] = contrato.inadimplente
    return cliente, overrides, buttons, menu_ctx, ai_ctx


async def send_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_message:
        return
    uid = str(update.effective_user.id) if update.effective_user else ""
    overrides: dict[str, str] | None = None
    buttons = resolve_bot_menu_buttons(None)
    menu_ctx = _menu_context(None, None, None)
    with SessionLocal() as db:
        if uid:
            _, overrides, buttons, menu_ctx, _ = _resolve_user_state(db, uid)
    text = render_template("bot_start", overrides=overrides, **menu_ctx)
    keyboard = _build_reply_keyboard(buttons)
    await update.effective_message.reply_text(text, reply_markup=keyboard)
    if context.user_data is not None:
        context.user_data["menu_shown"] = True


async def send_contextual_reply(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    user_message: str,
) -> None:
    if not update.effective_message:
        return
    uid = str(update.effective_user.id) if update.effective_user else ""
    overrides: dict[str, str] | None = None
    menu_ctx = _menu_context(None, None, None)
    ai_ctx: dict = {}
    cliente: Cliente | None = None
    with SessionLocal() as db:
        cliente, overrides, _, menu_ctx, ai_ctx = _resolve_user_state(db, uid)

    history: list[dict[str, str]] = list(
        (context.user_data or {}).get("chat_history", [])
    )
    intent = detect_intent(user_message)
    ai_ctx = ai_context_from_menu(menu_ctx, user_message=user_message)

    reply = ai_reply(user_message=user_message, context=ai_ctx, history=history or None)
    if not reply:
        reply = contextual_reply_text(
            user_message=user_message,
            overrides=overrides,
            menu_ctx=menu_ctx,
            intent=intent,
        )

    await update.effective_message.reply_text(reply)
    with SessionLocal() as db:
        if not cliente and uid:
            cliente, _, _, menu_ctx, _ = _resolve_user_state(db, uid)
        _notify_owner_contact(
            db,
            cliente=cliente,
            uid=uid,
            user_message=user_message,
            menu_ctx=menu_ctx,
        )
    if context.user_data is not None:
        context.user_data["chat_history"] = append_history(
            append_history(history, "user", user_message),
            "assistant",
            reply,
        )


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await send_menu(update, context)


async def cmd_promessa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_message:
        return
    uid = str(update.effective_user.id) if update.effective_user else ""
    overrides: dict[str, str] | None = None
    if uid:
        with SessionLocal() as db:
            _, overrides, _ = _cliente_for_telegram(db, uid)

    if not context.args or len(context.args) < 2:
        await update.effective_message.reply_text(
            render_template("bot_promessa_usage", overrides=overrides)
        )
        return
    try:
        days = int(context.args[0])
    except ValueError:
        await update.effective_message.reply_text(
            render_template("bot_promessa_invalid_days", overrides=overrides)
        )
        return
    notas = " ".join(context.args[1:])
    if not uid:
        await update.effective_message.reply_text(
            render_template("bot_promessa_no_user", overrides=overrides)
        )
        return
    ok = False
    try:
        with SessionLocal() as db:
            try:
                ok = record_promessa_from_telegram_user(
                    db, telegram_user_id=uid, days=days, notas=notas
                )
            except Exception:
                db.rollback()
                raise
    except Exception:
        await update.effective_message.reply_text(
            render_template("bot_promessa_error", overrides=overrides)
        )
        return
    if ok:
        await update.effective_message.reply_text(
            render_template("bot_promessa_success", overrides=overrides)
        )
    else:
        await update.effective_message.reply_text(
            render_template("bot_promessa_not_found", overrides=overrides)
        )


async def cmd_pix(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_message:
        return
    uid = str(update.effective_user.id) if update.effective_user else ""
    if not uid:
        return

    # Coleta todos os dados do banco e fecha a sessão ANTES de qualquer I/O de rede
    reply_template: str | None = None
    reply_kwargs: dict = {}
    pix_code_for_qr: str | None = None
    overrides: dict[str, str] | None = None

    with SessionLocal() as db:
        cliente, overrides, _ = _cliente_for_telegram(db, uid)
        if not cliente:
            reply_template = "bot_promessa_not_found"
        else:
            ct = _active_contrato(db, cliente.id)
            if not ct:
                reply_template = "bot_promessa_not_found"
            else:
                cob = get_open_cobranca(db, ct.id)
                if not cob:
                    reply_template = "overdue_no_pix"
                else:
                    op = db.get(Operacao, ct.operacao_id)
                    amounts = charge_amounts_for_cobranca(cob, ct, op, date.today()) if op else None
                    total = amounts.valor_total if amounts else cob.valor

                    # Breakdown: mostra discriminação se houver juros ou multa
                    if amounts and (amounts.multa > 0 or amounts.juros > 0):
                        valor_detalhado = (
                            f"Aluguel: {format_brl(ct.valor_recorrente)} + "
                            f"Multa: {format_brl(amounts.multa)} + "
                            f"Juros: {format_brl(amounts.juros)} = "
                            f"Total: {format_brl(total)}"
                        )
                    else:
                        valor_detalhado = f"Total: {format_brl(total)}"

                    portal_url = ensure_portal_url_for_cobranca(db, cob)
                    db.commit()
                    pix_block = cob.pix_copia_cola or ""
                    vencimento = cob.vencimento.isoformat()

                    if portal_url:
                        reply_template = "bot_pix_portal"
                        reply_kwargs = {
                            "vencimento": vencimento,
                            "valor_detalhado": valor_detalhado,
                            "valor_total": str(total),
                            "portal_url": portal_url,
                            "pix_block": f"Pix copia e cola:\n{pix_block}" if pix_block else "",
                        }
                    elif pix_block:
                        reply_template = "bot_pix"
                        reply_kwargs = {
                            "vencimento": vencimento,
                            "valor_detalhado": valor_detalhado,
                            "valor_total": str(total),
                            "pix_copia_cola": pix_block,
                        }
                    else:
                        reply_template = "overdue_no_pix"

                    if pix_block:
                        pix_code_for_qr = pix_block

    # Sessão fechada — envia QR e mensagem sem segurar conexão de banco
    if pix_code_for_qr:
        qr_bytes = _make_pix_qr_bytes(pix_code_for_qr)
        if qr_bytes:
            await update.effective_message.reply_photo(
                _io.BytesIO(qr_bytes),
                caption=reply_kwargs.get("valor_detalhado", ""),
            )

    await update.effective_message.reply_text(
        render_template(reply_template, overrides=overrides, **reply_kwargs)
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_message:
        return
    uid = str(update.effective_user.id) if update.effective_user else ""
    if not uid:
        return
    with SessionLocal() as db:
        cliente, overrides, _ = _cliente_for_telegram(db, uid)
        if not cliente:
            await update.effective_message.reply_text(
                render_template("bot_promessa_not_found", overrides=overrides)
            )
            return
        ct = _active_contrato(db, cliente.id)
        if not ct:
            await update.effective_message.reply_text(
                render_template("bot_promessa_not_found", overrides=overrides)
            )
            return
        promessa = ct.promessa_pagamento_em.isoformat() if ct.promessa_pagamento_em else "—"
        await update.effective_message.reply_text(
            render_template(
                "bot_status",
                overrides=overrides,
                proximo_vencimento=ct.proximo_vencimento.isoformat(),
                inadimplente="sim" if ct.inadimplente else "não",
                promessa_pagamento_em=promessa,
            )
        )


async def cmd_ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_message:
        return
    uid = str(update.effective_user.id) if update.effective_user else ""
    question = " ".join(context.args) if context.args else "Como usar o bot?"
    ctx: dict = {}
    overrides: dict[str, str] | None = None
    history: list[dict[str, str]] = list(context.user_data.get("chat_history", [])) if context.user_data else []
    if uid:
        with SessionLocal() as db:
            _, overrides, _, menu_ctx, ctx = _resolve_user_state(db, uid)
            ctx = ai_context_from_menu(menu_ctx, user_message=question)
    ai = ai_reply(user_message=question, context=ctx, history=history or None)
    if ai:
        await update.effective_message.reply_text(ai)
        if context.user_data is not None:
            context.user_data["chat_history"] = append_history(
                append_history(history, "user", question),
                "assistant",
                ai,
            )
    else:
        await update.effective_message.reply_text(render_template("bot_ajuda", overrides=overrides))


async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await send_menu(update, context)


async def _dispatch_menu_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    command: str,
) -> bool:
    """Executa comando integrado ou personalizado do menu. Retorna True se tratou."""
    if not update.effective_message:
        return False
    if command == "menu":
        await send_menu(update, context)
        return True
    handlers = {
        "promessa": cmd_promessa,
        "pix": cmd_pix,
        "status": cmd_status,
        "ajuda": cmd_ajuda,
    }
    handler = handlers.get(command)
    if handler:
        await handler(update, context)
        return True
    uid = str(update.effective_user.id) if update.effective_user else ""
    with SessionLocal() as db:
        cliente, _, buttons, menu_ctx, _ = _resolve_user_state(db, uid)
    btn = find_menu_button_by_command(command, buttons)
    if btn and btn.get("response"):
        text = render_menu_button_response(btn, menu_ctx=menu_ctx)
        await update.effective_message.reply_text(text)
        with SessionLocal() as db:
            if not cliente and uid:
                cliente, _, _, menu_ctx, _ = _resolve_user_state(db, uid)
            _notify_owner_contact(
                db,
                cliente=cliente,
                uid=uid,
                user_message=update.effective_message.text or btn["label"],
                menu_ctx=menu_ctx,
                button=btn,
            )
        return True
    return False


async def handle_slash_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_message or not update.effective_message.text:
        return
    cmd = update.effective_message.text.split()[0][1:].split("@")[0].lower()
    if await _dispatch_menu_command(update, context, cmd):
        return
    uid = str(update.effective_user.id) if update.effective_user else ""
    overrides: dict[str, str] | None = None
    if uid:
        with SessionLocal() as db:
            _, overrides, _, _, _ = _resolve_user_state(db, uid)
    await update.effective_message.reply_text(
        render_template("bot_comando_desconhecido", overrides=overrides, comando=cmd)
    )


async def _dispatch_command(command: str, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _dispatch_menu_command(update, context, command)


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_message or not update.effective_message.text:
        return
    uid = str(update.effective_user.id) if update.effective_user else ""
    text = update.effective_message.text
    buttons = resolve_bot_menu_buttons(None)
    if uid:
        with SessionLocal() as db:
            _, _, buttons = _cliente_for_telegram(db, uid)
    command = match_button_command(text, buttons)
    if command:
        button = _find_menu_button_by_label(text, buttons)
        await _dispatch_command(command, update, context)
        if button and uid and not button.get("response"):
            with SessionLocal() as db:
                cliente, _, _, menu_ctx, _ = _resolve_user_state(db, uid)
                _notify_owner_contact(
                    db,
                    cliente=cliente,
                    uid=uid,
                    user_message=text,
                    menu_ctx=menu_ctx,
                    button=button,
                )
        return
    if is_menu_request(text):
        await send_menu(update, context)
        return
    await send_contextual_reply(update, context, user_message=text)


def main() -> None:
    import threading
    import time

    from motopay.infrastructure.redis_client import get_redis_connection

    def _heartbeat_loop() -> None:
        r = get_redis_connection()
        while True:
            r.setex("bot:heartbeat", 60, "1")
            time.sleep(30)

    threading.Thread(target=_heartbeat_loop, daemon=True, name="bot-heartbeat").start()

    token = get_settings().telegram_bot_token
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("menu", cmd_menu))
    app.add_handler(CommandHandler("promessa", cmd_promessa))
    app.add_handler(CommandHandler("pix", cmd_pix))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("ajuda", cmd_ajuda))
    app.add_handler(MessageHandler(filters.COMMAND, handle_slash_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
