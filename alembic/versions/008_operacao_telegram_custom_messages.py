"""operacao telegram custom messages

Revision ID: 008_telegram_custom_msgs
Revises: 007_contrato_data_fim_vigencia
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "008_telegram_custom_msgs"
down_revision: str | None = "007_contrato_data_fim_vigencia"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "operacoes",
        sa.Column("telegram_custom_messages", JSONB(), nullable=True, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("operacoes", "telegram_custom_messages")
