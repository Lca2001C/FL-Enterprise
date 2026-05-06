"""Publicação de eventos de domínio (persistência + fila Celery)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from motopay.domain.enums import DomainEventType
from motopay.infrastructure.db.models import EventoDominio
from motopay.infrastructure.messaging.tasks import handle_domain_event


def publish_task_after_commit(db: Session, tipo: DomainEventType, payload: dict[str, Any]) -> None:
    ev = EventoDominio(tipo=tipo.value, payload=payload)
    db.add(ev)
    db.flush()
    eid = ev.id
    db.commit()
    handle_domain_event.delay(eid)
