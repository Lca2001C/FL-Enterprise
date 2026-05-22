from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from motopay.infrastructure.db.models import Operacao


@dataclass(frozen=True)
class LateAmounts:
    dias_atraso: int
    multa: Decimal
    juros: Decimal
    valor_total: Decimal


def calculate_late_amounts(
    *,
    valor_base: Decimal,
    vencimento: date,
    operacao: Operacao | None,
    today: date,
) -> LateAmounts:
    """Multa fixa + juros diários sobre valor_base quando vencimento < today."""
    if vencimento >= today:
        base = valor_base.quantize(Decimal("0.01"))
        return LateAmounts(dias_atraso=0, multa=Decimal(0), juros=Decimal(0), valor_total=base)

    m_pct = (operacao.multa_fixa_percentual / Decimal("100")) if operacao else Decimal(0)
    j_pct = (operacao.juros_diario_percentual / Decimal("100")) if operacao else Decimal(0)
    dias_atraso = (today - vencimento).days
    multa = (valor_base * m_pct).quantize(Decimal("0.01"))
    juros = (valor_base * j_pct * dias_atraso).quantize(Decimal("0.01"))
    valor_total = (valor_base + multa + juros).quantize(Decimal("0.01"))
    return LateAmounts(
        dias_atraso=dias_atraso,
        multa=multa,
        juros=juros,
        valor_total=valor_total,
    )
