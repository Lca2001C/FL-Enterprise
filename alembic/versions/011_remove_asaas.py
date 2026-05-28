"""remove asaas integration

Revision ID: 011_remove_asaas
Revises: 010_telegram_bot_menu
Create Date: 2026-05-27

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "011_remove_asaas"
down_revision: str | None = "010_telegram_bot_menu"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE cobrancas
        SET mercadopago_payment_id = asaas_payment_id
        WHERE mercadopago_payment_id IS NULL AND asaas_payment_id IS NOT NULL
        """
    )
    op.execute("UPDATE cobrancas SET payment_gateway = 'mercadopago' WHERE payment_gateway = 'asaas'")

    op.drop_constraint("cobrancas_asaas_payment_id_key", "cobrancas", type_="unique")
    op.drop_column("cobrancas", "asaas_payment_id")
    op.alter_column(
        "cobrancas",
        "payment_gateway",
        server_default="mercadopago",
        existing_type=sa.String(length=32),
        existing_nullable=False,
    )

    op.drop_column("clientes", "asaas_customer_id")
    op.drop_column("contratos", "asaas_customer_id")
    op.drop_column("contratos", "asaas_subscription_id")
    op.drop_column("operacoes", "payment_provider")


def downgrade() -> None:
    op.add_column(
        "operacoes",
        sa.Column("payment_provider", sa.String(length=32), server_default="asaas", nullable=False),
    )
    op.add_column("contratos", sa.Column("asaas_subscription_id", sa.String(length=64), nullable=True))
    op.add_column("contratos", sa.Column("asaas_customer_id", sa.String(length=64), nullable=True))
    op.add_column("clientes", sa.Column("asaas_customer_id", sa.String(length=64), nullable=True))

    op.alter_column(
        "cobrancas",
        "payment_gateway",
        server_default="asaas",
        existing_type=sa.String(length=32),
        existing_nullable=False,
    )
    op.add_column("cobrancas", sa.Column("asaas_payment_id", sa.String(length=64), nullable=True))
    op.create_unique_constraint("cobrancas_asaas_payment_id_key", "cobrancas", ["asaas_payment_id"])
