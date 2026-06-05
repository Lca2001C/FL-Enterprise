"""MP enterprise: portal token, refunds, oauth, disputes

Revision ID: 021_mp_enterprise
Revises: 020_contrato_mp_subscription_status
Create Date: 2026-06-01

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "021_mp_enterprise"
down_revision: str | None = "020_contrato_mp_subscription_status"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "cobrancas",
        sa.Column("payment_portal_token", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "cobrancas",
        sa.Column("valor_estornado", sa.Numeric(14, 2), server_default="0", nullable=False),
    )
    op.add_column(
        "cobrancas",
        sa.Column("mercadopago_dispute_status", sa.String(length=32), nullable=True),
    )
    op.create_index(
        "ix_cobrancas_payment_portal_token",
        "cobrancas",
        ["payment_portal_token"],
        unique=True,
    )
    op.add_column(
        "operacoes",
        sa.Column("mercadopago_refresh_token", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "operacoes",
        sa.Column("mercadopago_oauth_user_id", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "operacoes",
        sa.Column("mercadopago_oauth_expires_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("operacoes", "mercadopago_oauth_expires_at")
    op.drop_column("operacoes", "mercadopago_oauth_user_id")
    op.drop_column("operacoes", "mercadopago_refresh_token")
    op.drop_index("ix_cobrancas_payment_portal_token", table_name="cobrancas")
    op.drop_column("cobrancas", "mercadopago_dispute_status")
    op.drop_column("cobrancas", "valor_estornado")
    op.drop_column("cobrancas", "payment_portal_token")
