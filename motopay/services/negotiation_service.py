from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from motopay.config import app_today
from motopay.domain.enums import ContratoStatus
from motopay.infrastructure.db.models import Cliente, Contrato


def record_promessa_from_telegram_user(
    db: Session, *, telegram_user_id: str, days: int, notas: str
) -> bool:
    c = db.scalars(select(Cliente).where(Cliente.telegram_id == telegram_user_id)).first()
    if not c:
        return False
    ct = db.scalars(
        select(Contrato)
        .where(Contrato.cliente_id == c.id, Contrato.status == ContratoStatus.ATIVO.value)
        .order_by(Contrato.id.desc())
    ).first()
    if not ct:
        return False
    ct.promessa_pagamento_em = app_today() + timedelta(days=days)
    ct.promessa_notas = notas[:2000]
    db.add(ct)
    db.commit()
    return True
