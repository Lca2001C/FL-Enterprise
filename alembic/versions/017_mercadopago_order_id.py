"""cobranca mercadopago_order_id

Revision ID: 017_mercadopago_order_id
Revises: 016_cobranca_payment_method_type
Create Date: 2026-06-01

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "017_mercadopago_order_id"
down_revision: str | None = "016_cobranca_payment_method_type"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "cobrancas",
        sa.Column("mercadopago_order_id", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_cobrancas_mercadopago_order_id",
        "cobrancas",
        ["mercadopago_order_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_cobrancas_mercadopago_order_id", table_name="cobrancas")
    op.drop_column("cobrancas", "mercadopago_order_id")
