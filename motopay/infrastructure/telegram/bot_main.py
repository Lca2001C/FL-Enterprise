"""Telegram bot (polling). Comandos: /start, /promessa <dias> <texto>."""

from __future__ import annotations

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from motopay.config import get_settings
from motopay.infrastructure.db.session import SessionLocal
from motopay.services.negotiation_service import record_promessa_from_telegram_user


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(
            "MotoPay: envie /promessa <dias> <motivo> para registrar uma promessa de pagamento."
        )


async def cmd_promessa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_message or not context.args or len(context.args) < 2:
        if update.effective_message:
            await update.effective_message.reply_text("Uso: /promessa 3 pagar na próxima sexta-feira")
        return
    try:
        days = int(context.args[0])
    except ValueError:
        await update.effective_message.reply_text("Informe um número válido de dias.")
        return
    notas = " ".join(context.args[1:])
    uid = str(update.effective_user.id) if update.effective_user else ""
    db = SessionLocal()
    try:
        ok = record_promessa_from_telegram_user(db, telegram_user_id=uid, days=days, notas=notas)
    finally:
        db.close()
    if ok:
        await update.effective_message.reply_text("Registramos sua promessa. Obrigado pelo retorno.")
    else:
        await update.effective_message.reply_text(
            "Não localizamos seu cadastro com este Telegram. Peça ao operador para informar seu ID."
        )


def main() -> None:
    token = get_settings().telegram_bot_token
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("promessa", cmd_promessa))
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
