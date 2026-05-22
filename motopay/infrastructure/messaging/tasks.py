from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from motopay.config import get_settings
from motopay.domain.enums import ContratoStatus, DomainEventType
from motopay.infrastructure.db.models import Cliente, Contrato, EventoDominio, Moto, Operacao
from motopay.infrastructure.db.session import SessionLocal
from motopay.infrastructure.messaging.celery_app import celery_app
from motopay.infrastructure.telegram.notify import (
    TelegramPermanentError,
    TelegramTransientError,
    send_telegram_html,
    send_telegram_text,
)
from motopay.infrastructure.telegram.templates import build_overdue_html, render_template
from motopay.services.billing_service import late_amounts_for_contrato, refresh_overdue_pix
from motopay.services.scoring_service import effective_escalation_level, recalculate_cliente_score

logger = logging.getLogger(__name__)

_RETRY_KW = dict(
    autoretry_for=(TelegramTransientError,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=5,
)


def _template_overrides(db: Session, operacao_id: int | None) -> dict[str, str] | None:
    if operacao_id is None:
        return None
    op = db.get(Operacao, operacao_id)
    return op.telegram_templates if op else None


def _mark_telegram_sent(db: Session, contrato_id: int | None, today: date) -> None:
    if contrato_id is None:
        return
    ct = db.get(Contrato, int(contrato_id))
    if ct:
        ct.ultima_cobranca_telegram_em = today
        db.add(ct)


@celery_app.task(
    bind=True, name="motopay.infrastructure.messaging.tasks.handle_domain_event", **_RETRY_KW
)
def handle_domain_event(self, event_id: int) -> None:
    db = SessionLocal()
    try:
        ev = db.get(EventoDominio, event_id)
        if not ev or ev.processado_em is not None:
            return

        settings = get_settings()
        tz = ZoneInfo(settings.app_timezone)
        today = datetime.now(tz).date()

        chat_id: str | None = None
        message: str | None = None
        use_html = False
        contrato_id_for_mark: int | None = None
        operacao_id = ev.payload.get("operacao_id")
        overrides = _template_overrides(db, int(operacao_id) if operacao_id is not None else None)

        if ev.tipo == DomainEventType.PAGAMENTO_CONFIRMADO.value:
            cid = ev.payload.get("cliente_id")
            if cid:
                cliente = db.get(Cliente, int(cid))
                if cliente and cliente.telegram_id:
                    chat_id = cliente.telegram_id
                    message = render_template("pagamento_confirmado", overrides=overrides)
        elif ev.tipo == DomainEventType.CLIENTE_INADIMPLENTE.value:
            cid = ev.payload.get("cliente_id")
            nivel = int(ev.payload.get("nivel_escalonamento", 0))
            contrato_id_for_mark = ev.payload.get("contrato_id")
            if cid:
                cliente = db.get(Cliente, int(cid))
                if cliente and cliente.telegram_id:
                    chat_id = cliente.telegram_id
                    message = build_overdue_html(
                        overrides=overrides, payload=ev.payload, nivel=nivel
                    )
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
                        message = render_template(
                            "moto_manutencao", overrides=overrides, placa=placa
                        )

        if chat_id and message:
            try:
                if use_html:
                    send_telegram_html(chat_id=chat_id, html=message)
                else:
                    send_telegram_text(chat_id=chat_id, text=message)
                if ev.tipo == DomainEventType.CLIENTE_INADIMPLENTE.value:
                    _mark_telegram_sent(db, contrato_id_for_mark, today)
            except TelegramPermanentError as e:
                logger.warning(
                    "domain_event_telegram_skipped event_id=%s tipo=%s contrato_id=%s: %s",
                    event_id,
                    ev.tipo,
                    contrato_id_for_mark,
                    e,
                )
            except TelegramTransientError:
                raise

        ev.processado_em = datetime.now(UTC)
        db.add(ev)
        db.commit()
    finally:
        db.close()


@celery_app.task(
    bind=True, name="motopay.infrastructure.messaging.tasks.send_d1_reminder", **_RETRY_KW
)
def send_d1_reminder(self, contrato_id: int) -> None:
    db = SessionLocal()
    try:
        ct = db.get(Contrato, contrato_id)
        if not ct or ct.status != ContratoStatus.ATIVO.value:
            return
        cliente = db.get(Cliente, ct.cliente_id)
        if not cliente or not cliente.telegram_id:
            return
        overrides = _template_overrides(db, ct.operacao_id)
        text = render_template(
            "d1_reminder",
            overrides=overrides,
            proximo_vencimento=ct.proximo_vencimento,
            contrato_id=ct.id,
            valor_recorrente=f"{ct.valor_recorrente:.2f}",
        )
        try:
            send_telegram_text(chat_id=cliente.telegram_id, text=text)
        except TelegramPermanentError as e:
            logger.warning("d1_reminder_permanent_failure contrato_id=%s: %s", contrato_id, e)
    finally:
        db.close()


@celery_app.task(
    bind=True, name="motopay.infrastructure.messaging.tasks.send_d0_reminder", **_RETRY_KW
)
def send_d0_reminder(self, contrato_id: int) -> None:
    db = SessionLocal()
    try:
        ct = db.get(Contrato, contrato_id)
        if not ct or ct.status != ContratoStatus.ATIVO.value:
            return
        cliente = db.get(Cliente, ct.cliente_id)
        if not cliente or not cliente.telegram_id:
            return
        overrides = _template_overrides(db, ct.operacao_id)
        text = render_template(
            "d0_reminder",
            overrides=overrides,
            proximo_vencimento=ct.proximo_vencimento,
            contrato_id=ct.id,
            valor_recorrente=f"{ct.valor_recorrente:.2f}",
        )
        try:
            send_telegram_text(chat_id=cliente.telegram_id, text=text)
        except TelegramPermanentError as e:
            logger.warning("d0_reminder_permanent_failure contrato_id=%s: %s", contrato_id, e)
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
        _process_d0(db, today)
        _process_d1(db, tomorrow)
        _process_delinquency(db, today)
    finally:
        db.close()


def _process_d0(db: Session, today: date) -> None:
    rows = db.scalars(
        select(Contrato).where(
            Contrato.status == ContratoStatus.ATIVO.value,
            Contrato.proximo_vencimento == today,
        )
    ).all()
    for ct in rows:
        send_d0_reminder.delay(ct.id)


def _process_d1(db: Session, tomorrow: date) -> None:
    rows = db.scalars(
        select(Contrato).where(
            Contrato.status == ContratoStatus.ATIVO.value,
            Contrato.proximo_vencimento == tomorrow,
        )
    ).all()
    for ct in rows:
        send_d1_reminder.delay(ct.id)


def _base_escalation(days_late: int) -> int:
    if days_late >= 7:
        return 2
    if days_late >= 3:
        return 1
    return 0


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
        base_level = _base_escalation(days_late)
        cliente = db.get(Cliente, ct.cliente_id)
        score = int(cliente.score) if cliente else 50
        ct.nivel_escalonamento_cobranca = effective_escalation_level(base_level, score)
        db.add(ct)

        refresh_overdue_pix(db, contrato=ct, today=today)
        amounts = late_amounts_for_contrato(db, ct, today)

        skip_telegram = False
        if ct.promessa_pagamento_em and ct.promessa_pagamento_em >= today:
            skip_telegram = True
        if ct.ultima_cobranca_telegram_em == today:
            skip_telegram = True

        if not skip_telegram:
            from motopay.services.billing_service import get_open_cobranca

            open_cob = get_open_cobranca(db, ct.id)
            ev = EventoDominio(
                tipo=DomainEventType.CLIENTE_INADIMPLENTE.value,
                payload={
                    "contrato_id": ct.id,
                    "cliente_id": ct.cliente_id,
                    "operacao_id": ct.operacao_id,
                    "nivel_escalonamento": ct.nivel_escalonamento_cobranca,
                    "dias_atraso": days_late,
                    "cobranca_id": open_cob.id if open_cob else None,
                    "valor_base": str(ct.valor_recorrente),
                    "multa": str(amounts.multa),
                    "juros": str(amounts.juros),
                    "valor_total": str(amounts.valor_total),
                    "pix_copia_cola": open_cob.pix_copia_cola if open_cob else None,
                },
            )
            db.add(ev)
            db.flush()
            pending_events.append(ev.id)

        cid = ct.cliente_id
        cliente_max_days_late[cid] = max(cliente_max_days_late.get(cid, 0), days_late)

    for cid, max_days in cliente_max_days_late.items():
        cliente = db.get(Cliente, cid)
        if cliente:
            recalculate_cliente_score(db, cliente, late_penalty=min(20, max_days * 2))

    db.commit()
    for eid in pending_events:
        handle_domain_event.delay(eid)
