"""add asaas_customer_id to clientes

Revision ID: 002
Revises: 001_initial
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "002_cliente_asaas"
down_revision: str | None = "001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("clientes", sa.Column("asaas_customer_id", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("clientes", "asaas_customer_id")
