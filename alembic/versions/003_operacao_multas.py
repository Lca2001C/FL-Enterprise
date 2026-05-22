"""multa e juros por operacao

Revision ID: 003_operacao_multas
Revises: 002_cliente_asaas
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "003_operacao_multas"
down_revision: str | None = "002_cliente_asaas"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "operacoes",
        sa.Column("multa_fixa_percentual", sa.Numeric(5, 2), server_default="2.00", nullable=False),
    )
    op.add_column(
        "operacoes",
        sa.Column(
            "juros_diario_percentual", sa.Numeric(5, 2), server_default="0.10", nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_column("operacoes", "juros_diario_percentual")
    op.drop_column("operacoes", "multa_fixa_percentual")
