from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from motopay.config import get_settings
from motopay.domain.enums import ContratoStatus, DomainEventType
from motopay.infrastructure.db.models import Cliente, Contrato, EventoDominio
from motopay.infrastructure.db.session import SessionLocal
from motopay.infrastructure.messaging.celery_app import celery_app
from motopay.infrastructure.telegram.notify import send_telegram_text
from motopay.services.scoring_service import recalculate_cliente_score


@celery_app.task(name="motopay.infrastructure.messaging.tasks.handle_domain_event")
def handle_domain_event(event_id: int) -> None:
    db = SessionLocal()
    try:
        ev = db.get(EventoDominio, event_id)
        if not ev or ev.processado_em is not None:
            return
        if ev.tipo == DomainEventType.PAGAMENTO_CONFIRMADO.value:
            cid = ev.payload.get("cliente_id")
            if cid:
                cliente = db.get(Cliente, int(cid))
                if cliente and cliente.telegram_id:
                    send_telegram_text(
                        chat_id=cliente.telegram_id,
                        text="✅ Pagamento confirmado! Obrigado. Sua locação segue em dia.",
                    )
        elif ev.tipo == DomainEventType.CLIENTE_INADIMPLENTE.value:
            cid = ev.payload.get("cliente_id")
            nivel = int(ev.payload.get("nivel_escalonamento", 0))
            if cid:
                cliente = db.get(Cliente, int(cid))
                if cliente and cliente.telegram_id:
                    msgs = [
                        "Olá! Identificamos pendência no pagamento. Por favor regularize quando puder.",
                        "⚠️ Atenção: seu pagamento está em atraso. Evite juros e bloqueios.",
                        "🔴 Cobrança firme: existe débito em aberto. Entre em contato para negociar.",
                    ]
                    send_telegram_text(chat_id=cliente.telegram_id, text=msgs[min(nivel, 2)])
        elif ev.tipo == DomainEventType.MOTO_EM_MANUTENCAO.value:
            # Reservado: notificar canal interno / donos quando configurado
            pass
        ev.processado_em = datetime.now(timezone.utc)
        db.add(ev)
        db.commit()
    finally:
        db.close()


@celery_app.task(name="motopay.infrastructure.messaging.tasks.send_d1_reminder")
def send_d1_reminder(contrato_id: int) -> None:
    db = SessionLocal()
    try:
        ct = db.get(Contrato, contrato_id)
        if not ct or ct.status != ContratoStatus.ATIVO.value:
            return
        cliente = db.get(Cliente, ct.cliente_id)
        if not cliente or not cliente.telegram_id:
            return
        send_telegram_text(
            chat_id=cliente.telegram_id,
            text=(
                f"Lembrete: amanhã ({ct.proximo_vencimento}) vence o pagamento "
                f"do contrato #{ct.id} no valor de R$ {ct.valor_recorrente:.2f}."
            ),
        )
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
        cliente = db.get(Cliente, ct.cliente_id)
        if cliente:
            recalculate_cliente_score(db, cliente, late_penalty=min(20, days_late * 2))
        ev = EventoDominio(
            tipo=DomainEventType.CLIENTE_INADIMPLENTE.value,
            payload={
                "contrato_id": ct.id,
                "cliente_id": ct.cliente_id,
                "operacao_id": ct.operacao_id,
                "nivel_escalonamento": ct.nivel_escalonamento_cobranca,
                "dias_atraso": days_late,
            },
        )
        db.add(ev)
        db.flush()
        pending_events.append(ev.id)
    db.commit()
    for eid in pending_events:
        handle_domain_event.delay(eid)
