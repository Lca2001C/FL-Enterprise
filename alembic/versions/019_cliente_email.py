"""cliente email for Mercado Pago payer

Revision ID: 019_cliente_email
Revises: 018_merge_heads
Create Date: 2026-06-01

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "019_cliente_email"
down_revision: str | None = "018_merge_heads"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column("clientes", sa.Column("email", sa.String(length=320), nullable=True))


def downgrade() -> None:
    op.drop_column("clientes", "email")
