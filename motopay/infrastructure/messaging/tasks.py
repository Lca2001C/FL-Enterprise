from __future__ import annotations

import html
import logging
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from motopay.config import get_settings
from motopay.domain.enums import ContratoStatus, DomainEventType
from motopay.infrastructure.db.models import Cliente, Contrato, EventoDominio, Moto
from motopay.infrastructure.db.session import SessionLocal
from motopay.infrastructure.messaging.celery_app import celery_app
from motopay.infrastructure.telegram.notify import (
    TelegramPermanentError,
    TelegramTransientError,
    send_telegram_html,
    send_telegram_text,
)
from motopay.services.billing_service import late_amounts_for_contrato, refresh_overdue_pix
from motopay.services.scoring_service import recalculate_cliente_score

logger = logging.getLogger(__name__)

_RETRY_KW = dict(
    autoretry_for=(TelegramTransientError,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=5,
)


def _format_brl(value: Decimal | float) -> str:
    return f"R$ {Decimal(value):.2f}".replace(".", ",")


def _build_overdue_telegram_message(*, payload: dict, nivel: int) -> str:
    dias = int(payload.get("dias_atraso", 0))
    valor_base = Decimal(str(payload.get("valor_base", 0)))
    multa = Decimal(str(payload.get("multa", 0)))
    juros = Decimal(str(payload.get("juros", 0)))
    valor_total = Decimal(str(payload.get("valor_total", 0)))
    pix = payload.get("pix_copia_cola") or ""

    tone = [
        "Olá! Identificamos pendência no pagamento. Segue o Pix atualizado:",
        "⚠️ Atenção: seu pagamento está em atraso. Use o Pix abaixo:",
        "🔴 Cobrança firme: existe débito em aberto. Pix atualizado abaixo:",
    ]
    intro = tone[min(nivel, 2)]

    lines = [
        html.escape(intro),
        "",
        html.escape(f"Pagamento em atraso ({dias} dia(s))"),
        html.escape(f"Aluguel: {_format_brl(valor_base)}"),
        html.escape(f"Multa: {_format_brl(multa)}"),
        html.escape(f"Juros: {_format_brl(juros)}"),
        html.escape(f"Total a pagar: {_format_brl(valor_total)}"),
    ]
    if pix:
        lines.extend(
            [
                "",
                html.escape("Pix (copia e cola):"),
                f"<code>{html.escape(str(pix))}</code>",
                "",
                html.escape("O Pix anterior foi cancelado; use apenas este código."),
            ]
        )
    else:
        lines.extend(
            [
                "",
                html.escape("Não foi possível gerar o Pix automaticamente. Fale com o operador."),
            ]
        )
    return "\n".join(lines)


@celery_app.task(bind=True, name="motopay.infrastructure.messaging.tasks.handle_domain_event", **_RETRY_KW)
def handle_domain_event(self, event_id: int) -> None:
    db = SessionLocal()
    try:
        ev = db.get(EventoDominio, event_id)
        if not ev or ev.processado_em is not None:
            return

        chat_id: str | None = None
        message: str | None = None
        use_html = False

        if ev.tipo == DomainEventType.PAGAMENTO_CONFIRMADO.value:
            cid = ev.payload.get("cliente_id")
            if cid:
                cliente = db.get(Cliente, int(cid))
                if cliente and cliente.telegram_id:
                    chat_id = cliente.telegram_id
                    message = "✅ Pagamento confirmado! Obrigado. Sua locação segue em dia."
        elif ev.tipo == DomainEventType.CLIENTE_INADIMPLENTE.value:
            cid = ev.payload.get("cliente_id")
            nivel = int(ev.payload.get("nivel_escalonamento", 0))
            if cid:
                cliente = db.get(Cliente, int(cid))
                if cliente and cliente.telegram_id:
                    chat_id = cliente.telegram_id
                    message = _build_overdue_telegram_message(payload=ev.payload, nivel=nivel)
                    use_html = True
        elif ev.tipo == DomainEventType.MOTO_EM_MANUTENCAO.value:
            moto_id = ev.payload.get("moto_id")
            if moto_id:
                moto = db.get(Moto, int(moto_id))
                ct = db.scalars(
                    select(Contrato).where(
                        Contrato.moto_id == int(moto_id),
                        Contrato.status == ContratoStatus.ATIVO.value,
                    )
                ).first()
                if ct:
                    cliente = db.get(Cliente, ct.cliente_id)
                    if cliente and cliente.telegram_id:
                        chat_id = cliente.telegram_id
                        placa = moto.placa if moto else str(moto_id)
                        message = (
                            f"🔧 A moto {placa} entrou em manutenção. "
                            "Entraremos em contato sobre prazos e substituição, se aplicável."
                        )

        if chat_id and message:
            try:
                if use_html:
                    send_telegram_html(chat_id=chat_id, html=message)
                else:
                    send_telegram_text(chat_id=chat_id, text=message)
            except TelegramPermanentError as e:
                logger.warning(
                    "domain_event_telegram_skipped event_id=%s tipo=%s: %s",
                    event_id,
                    ev.tipo,
                    e,
                )
            except TelegramTransientError:
                raise

        ev.processado_em = datetime.now(UTC)
        db.add(ev)
        db.commit()
    finally:
        db.close()


@celery_app.task(bind=True, name="motopay.infrastructure.messaging.tasks.send_d1_reminder", **_RETRY_KW)
def send_d1_reminder(self, contrato_id: int) -> None:
    db = SessionLocal()
    try:
        ct = db.get(Contrato, contrato_id)
        if not ct or ct.status != ContratoStatus.ATIVO.value:
            return
        cliente = db.get(Cliente, ct.cliente_id)
        if not cliente or not cliente.telegram_id:
            return
        try:
            send_telegram_text(
                chat_id=cliente.telegram_id,
                text=(
                    f"Lembrete: amanhã ({ct.proximo_vencimento}) vence o pagamento "
                    f"do contrato #{ct.id} no valor de R$ {ct.valor_recorrente:.2f}."
                ),
            )
        except TelegramPermanentError as e:
            logger.warning("d1_reminder_permanent_failure contrato_id=%s: %s", contrato_id, e)
    finally:
        db.close()


@celery_app.task(name="motopay.infrastructure.messaging.tasks.daily_automation_tick")
def daily_automation_tick() -> None:
    settings = get_settings()
    tz = ZoneInfo(settings.app_timezone)
    today = datetime.now(tz).date()
    tomorrow = today + timedelta(days=1)
    db = SessionLocal()
    try:
        _process_d1(db, tomorrow)
        _process_delinquency(db, today)
    finally:
        db.close()


def _process_d1(db: Session, tomorrow: date) -> None:
    rows = db.scalars(
        select(Contrato).where(
            Contrato.status == ContratoStatus.ATIVO.value,
            Contrato.proximo_vencimento == tomorrow,
        )
    ).all()
    for ct in rows:
        send_d1_reminder.delay(ct.id)


def _process_delinquency(db: Session, today: date) -> None:
    rows = db.scalars(
        select(Contrato).where(
            Contrato.status == ContratoStatus.ATIVO.value,
            Contrato.proximo_vencimento < today,
        )
    ).all()
    pending_events: list[int] = []
    cliente_max_days_late: dict[int, int] = {}
    for ct in rows:
        days_late = (today - ct.proximo_vencimento).days
        ct.inadimplente = True
        ct.dias_atraso_acumulado = days_late
        if days_late >= 7:
            ct.nivel_escalonamento_cobranca = 2
        elif days_late >= 3:
            ct.nivel_escalonamento_cobranca = max(ct.nivel_escalonamento_cobranca, 1)
        else:
            ct.nivel_escalonamento_cobranca = max(ct.nivel_escalonamento_cobranca, 0)
        db.add(ct)

        cob = refresh_overdue_pix(db, contrato=ct, today=today)
        amounts = late_amounts_for_contrato(db, ct, today)

        cid = ct.cliente_id
        cliente_max_days_late[cid] = max(cliente_max_days_late.get(cid, 0), days_late)
        ev = EventoDominio(
            tipo=DomainEventType.CLIENTE_INADIMPLENTE.value,
            payload={
                "contrato_id": ct.id,
                "cliente_id": ct.cliente_id,
                "operacao_id": ct.operacao_id,
                "nivel_escalonamento": ct.nivel_escalonamento_cobranca,
                "dias_atraso": days_late,
                "cobranca_id": cob.id if cob else None,
                "valor_base": str(ct.valor_recorrente),
                "multa": str(amounts.multa),
                "juros": str(amounts.juros),
                "valor_total": str(amounts.valor_total),
                "pix_copia_cola": cob.pix_copia_cola if cob else None,
            },
        )
        db.add(ev)
        db.flush()
        pending_events.append(ev.id)

    for cid, max_days in cliente_max_days_late.items():
        cliente = db.get(Cliente, cid)
        if cliente:
            recalculate_cliente_score(db, cliente, late_penalty=min(20, max_days * 2))

    db.commit()
    for eid in pending_events:
        handle_domain_event.delay(eid)
