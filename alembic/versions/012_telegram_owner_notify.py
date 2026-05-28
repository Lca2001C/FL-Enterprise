"""telegram owner notify settings

Revision ID: 012_telegram_owner_notify
Revises: 011_remove_asaas
Create Date: 2026-05-27

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "012_telegram_owner_notify"
down_revision: str | None = "011_remove_asaas"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "operacoes",
        sa.Column("telegram_owner_notify_id", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "operacoes",
        sa.Column(
            "telegram_owner_notify_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("operacoes", "telegram_owner_notify_enabled")
    op.drop_column("operacoes", "telegram_owner_notify_id")
