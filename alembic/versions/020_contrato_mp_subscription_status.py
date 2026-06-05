"""contrato mercadopago subscription status

Revision ID: 020_contrato_mp_subscription_status
Revises: 019_cliente_email
Create Date: 2026-06-01

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "020_contrato_mp_subscription_status"
down_revision: str | None = "019_cliente_email"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "contratos",
        sa.Column("mercadopago_subscription_status", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("contratos", "mercadopago_subscription_status")
