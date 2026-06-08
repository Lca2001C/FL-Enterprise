"""Mercado Pago como único gateway de pagamento

Revision ID: 009_mercadopago_only
Revises: 008_telegram_custom_msgs
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "009_mercadopago_only"
down_revision: str | None = "008_telegram_custom_msgs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return column in {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    # 011_remove_asaas pode já ter removido payment_provider; branch idempotente.
    if _has_column("operacoes", "payment_provider"):
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
    if _has_column("cobrancas", "payment_gateway"):
        op.alter_column(
            "cobrancas",
            "payment_gateway",
            server_default="mercadopago",
            existing_type=sa.String(32),
        )


def downgrade() -> None:
    if _has_column("operacoes", "payment_provider"):
        op.alter_column(
            "operacoes",
            "payment_provider",
            server_default="asaas",
            existing_type=sa.String(32),
        )
    if _has_column("cobrancas", "payment_gateway"):
        op.alter_column(
            "cobrancas",
            "payment_gateway",
            server_default="asaas",
            existing_type=sa.String(32),
        )
