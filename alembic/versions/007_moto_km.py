"""add moto km

Revision ID: 007_moto_km
Revises: 008_telegram_custom_msgs
Create Date: 2026-05-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "007_moto_km"
down_revision: str | None = "008_telegram_custom_msgs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "motos",
        sa.Column("km", sa.BigInteger(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("motos", "km")
