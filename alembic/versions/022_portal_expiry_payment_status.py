"""Portal expiry and MP payment status on cobrancas

Revision ID: 022_portal_expiry
Revises: 021_mp_enterprise
Create Date: 2026-06-01

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "022_portal_expiry"
down_revision: str | None = "021_mp_enterprise"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "cobrancas",
        sa.Column("payment_portal_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "cobrancas",
        sa.Column("mercadopago_payment_status", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("cobrancas", "mercadopago_payment_status")
    op.drop_column("cobrancas", "payment_portal_expires_at")
