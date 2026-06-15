"""MP OAuth: connection_status, account email, token columns as Text.

Revision ID: 026_mp_tenant_oauth
Revises: 025_contrato_numero
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "026_mp_tenant_oauth"
down_revision: str | None = "025_contrato_numero"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "operacoes",
        sa.Column(
            "mercadopago_connection_status",
            sa.String(length=32),
            nullable=False,
            server_default="disconnected",
        ),
    )
    op.add_column(
        "operacoes",
        sa.Column("mercadopago_account_email", sa.String(length=255), nullable=True),
    )
    op.alter_column(
        "operacoes",
        "mercadopago_access_token",
        existing_type=sa.String(length=512),
        type_=sa.Text(),
        existing_nullable=True,
    )
    op.alter_column(
        "operacoes",
        "mercadopago_refresh_token",
        existing_type=sa.String(length=512),
        type_=sa.Text(),
        existing_nullable=True,
    )

    op.execute(
        """
        UPDATE operacoes
        SET mercadopago_connection_status = 'connected'
        WHERE mercadopago_oauth_user_id IS NOT NULL
          AND mercadopago_oauth_user_id != ''
          AND mercadopago_access_token IS NOT NULL
          AND mercadopago_access_token != ''
          AND mercadopago_public_key IS NOT NULL
          AND mercadopago_public_key != ''
        """
    )


def downgrade() -> None:
    op.drop_column("operacoes", "mercadopago_account_email")
    op.drop_column("operacoes", "mercadopago_connection_status")
    op.alter_column(
        "operacoes",
        "mercadopago_access_token",
        existing_type=sa.Text(),
        type_=sa.String(length=512),
        existing_nullable=True,
    )
    op.alter_column(
        "operacoes",
        "mercadopago_refresh_token",
        existing_type=sa.Text(),
        type_=sa.String(length=512),
        existing_nullable=True,
    )
