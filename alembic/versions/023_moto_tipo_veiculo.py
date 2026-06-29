"""Add tipo column to motos table

Revision ID: 023_moto_tipo_veiculo
Revises: 022_portal_expiry
Create Date: 2026-06-08

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "023_moto_tipo_veiculo"
down_revision: str | None = "022_portal_expiry"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "motos",
        sa.Column("tipo", sa.String(length=32), nullable=False, server_default="moto"),
    )


def downgrade() -> None:
    op.drop_column("motos", "tipo")
