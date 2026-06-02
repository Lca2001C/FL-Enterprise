"""Mercado Pago como único gateway de pagamento

Revision ID: 009_mercadopago_only
Revises: 008_telegram_custom_msgs
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "009_mercadopago_only"
down_revision: str | None = "008_telegram_custom_msgs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _operacoes_has_payment_provider() -> bool:
    bind = op.get_bind()
    cols = {c["name"] for c in inspect(bind).get_columns("operacoes")}
    return "payment_provider" in cols


def upgrade() -> None:
    if _operacoes_has_payment_provider():
        op.alter_column(
            "operacoes",
            "payment_provider",
            server_default="mercadopago",
            existing_type=sa.String(32),
        )
        op.execute(
            "UPDATE operacoes SET payment_provider = 'mercadopago' "
            "WHERE payment_provider = 'asaas'"
        )

    op.alter_column(
        "cobrancas",
        "payment_gateway",
        server_default="mercadopago",
        existing_type=sa.String(32),
    )


def downgrade() -> None:
    if _operacoes_has_payment_provider():
        op.alter_column(
            "operacoes",
            "payment_provider",
            server_default="asaas",
            existing_type=sa.String(32),
        )
    op.alter_column(
        "cobrancas",
        "payment_gateway",
        server_default="asaas",
        existing_type=sa.String(32),
    )
