"""índice composto multas(moto_id, data)

Revision ID: 028_multas_moto_data_idx
Revises: 027_multas_anexos
Create Date: 2026-06-29

Acelera a subquery de multas por veículo usada no ranking de métricas
(analytics_service.moto_ranking), que filtra por moto_id + intervalo de datas.
A 027 indexou operacao_id/data/status, mas não moto_id.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "028_multas_moto_data_idx"
down_revision: str | None = "027_multas_anexos"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("ix_multas_moto_data", "multas", ["moto_id", "data"])


def downgrade() -> None:
    op.drop_index("ix_multas_moto_data", table_name="multas")
