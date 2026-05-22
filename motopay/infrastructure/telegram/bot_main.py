"""Telegram bot (polling). Comandos: /start, /promessa, /pix, /status, /ajuda."""

from __future__ import annotations

from sqlalchemy import select
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from motopay.config import get_settings
from motopay.domain.enums import ContratoStatus
from motopay.infrastructure.db.models import Cliente, Contrato, Operacao
from motopay.infrastructure.db.session import SessionLocal
from motopay.infrastructure.telegram.ai_agent import ai_reply
from motopay.infrastructure.telegram.templates import render_template
from motopay.services.billing_service import get_open_cobranca
from motopay.services.negotiation_service import record_promessa_from_telegram_user


def _cliente_for_telegram(db, telegram_user_id: str) -> tuple[Cliente | None, dict[str, str] | None]:
    cliente = db.scalars(select(Cliente).where(Cliente.telegram_id == telegram_user_id)).first()
    overrides: dict[str, str] | None = None
    if cliente:
        op = db.get(Operacao, cliente.operacao_id)
        overrides = op.telegram_templates if op else None
    return cliente, overrides


def _active_contrato(db, cliente_id: int) -> Contrato | None:
    return db.scalars(
        select(Contrato)
        .where(Contrato.cliente_id == cliente_id, Contrato.status == ContratoStatus.ATIVO.value)
        .order_by(Contrato.id.desc())
    ).first()


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_message:
        return
    uid = str(update.effective_user.id) if update.effective_user else ""
    overrides: dict[str, str] | None = None
    if uid:
        with SessionLocal() as db:
            _, overrides = _cliente_for_telegram(db, uid)
    await update.effective_message.reply_text(render_template("bot_start", overrides=overrides))


async def cmd_promessa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_message:
        return
    uid = str(update.effective_user.id) if update.effective_user else ""
    overrides: dict[str, str] | None = None
    if uid:
        with SessionLocal() as db:
            _, overrides = _cliente_for_telegram(db, uid)

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
                ok = record_promessa_from_telegram_user(db, telegram_user_id=uid, days=days, notas=notas)
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
    with SessionLocal() as db:
        cliente, overrides = _cliente_for_telegram(db, uid)
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
        cob = get_open_cobranca(db, ct.id)
        if not cob or not cob.pix_copia_cola:
            await update.effective_message.reply_text(
                render_template("overdue_no_pix", overrides=overrides)
            )
            return
        await update.effective_message.reply_text(
            render_template(
                "bot_pix",
                overrides=overrides,
                vencimento=cob.vencimento.isoformat(),
                valor_total=str(cob.valor),
                pix_copia_cola=cob.pix_copia_cola,
            )
        )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_message:
        return
    uid = str(update.effective_user.id) if update.effective_user else ""
    if not uid:
        return
    with SessionLocal() as db:
        cliente, overrides = _cliente_for_telegram(db, uid)
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
    if uid:
        with SessionLocal() as db:
            cliente, overrides = _cliente_for_telegram(db, uid)
            if cliente:
                ct = _active_contrato(db, cliente.id)
                ctx = {
                    "cliente": cliente.nome,
                    "score": cliente.score,
                    "inadimplente": ct.inadimplente if ct else False,
                    "proximo_vencimento": str(ct.proximo_vencimento) if ct else None,
                    "promessa": str(ct.promessa_pagamento_em) if ct and ct.promessa_pagamento_em else None,
                }
    ai = ai_reply(user_message=question, context=ctx)
    if ai:
        await update.effective_message.reply_text(ai)
    else:
        await update.effective_message.reply_text(render_template("bot_ajuda", overrides=overrides))


def main() -> None:
    token = get_settings().telegram_bot_token
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("promessa", cmd_promessa))
    app.add_handler(CommandHandler("pix", cmd_pix))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("ajuda", cmd_ajuda))
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
