"""telegram bot menu buttons

Revision ID: 010_telegram_bot_menu
Revises: 009_moto_imagem
Create Date: 2026-05-27

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "010_telegram_bot_menu"
down_revision: str | None = "009_moto_imagem"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "operacoes",
        sa.Column("telegram_bot_menu_buttons", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("operacoes", "telegram_bot_menu_buttons")
