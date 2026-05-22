"""telegram templates por operacao

Revision ID: 004_operacao_telegram_templates
Revises: 003_operacao_multas
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "004_operacao_telegram_templates"
down_revision: str | None = "003_operacao_multas"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "operacoes",
        sa.Column("telegram_templates", JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("operacoes", "telegram_templates")
