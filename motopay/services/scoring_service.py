from __future__ import annotations

from sqlalchemy.orm import Session

from motopay.infrastructure.db.models import Cliente


def effective_escalation_level(base: int, score: int) -> int:
    """Ajusta nível de cobrança Telegram conforme score do cliente."""
    level = int(base)
    if score >= 80:
        level = max(0, level - 1)
    elif score < 40 and level < 2:
        level = min(2, level + 1)
    return max(0, min(2, level))


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
