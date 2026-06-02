"""cobranca payment_method_type

Revision ID: 016_cobranca_payment_method_type
Revises: 015_cliente_mp_cards
Create Date: 2026-06-02

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "016_cobranca_payment_method_type"
down_revision: str | None = "015_cliente_mp_cards"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "cobrancas",
        sa.Column("payment_method_type", sa.String(length=32), nullable=True),
    )
    op.create_index("ix_cobrancas_payment_method_type", "cobrancas", ["payment_method_type"])


def downgrade() -> None:
    op.drop_index("ix_cobrancas_payment_method_type", table_name="cobrancas")
    op.drop_column("cobrancas", "payment_method_type")
