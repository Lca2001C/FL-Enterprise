from __future__ import annotations

from sqlalchemy.orm import Session

from motopay.infrastructure.db.models import Cliente


def recalculate_cliente_score(
    db: Session,
    cliente: Cliente,
    *,
    on_time_payment_delta: int = 0,
    late_penalty: int = 0,
) -> None:
    """Ajusta score 0–100 com deltas (MVP)."""
    s = int(cliente.score or 50) + on_time_payment_delta - late_penalty
    cliente.score = max(0, min(100, s))
    db.add(cliente)
    db.flush()
