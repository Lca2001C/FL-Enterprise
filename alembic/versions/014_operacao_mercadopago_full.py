"""operacao mercadopago public key and webhook secret

Revision ID: 014_operacao_mercadopago_full
Revises: 013_default_contato_button
Create Date: 2026-06-02

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "014_operacao_mercadopago_full"
down_revision: str | None = "013_default_contato_button"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "operacoes",
        sa.Column("mercadopago_public_key", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "operacoes",
        sa.Column("mercadopago_webhook_secret", sa.String(length=256), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("operacoes", "mercadopago_webhook_secret")
    op.drop_column("operacoes", "mercadopago_public_key")
