"""product expansion: payment provider, MP, promessa dedup, cliente login

Revision ID: 005_product_expansion
Revises: 004_operacao_telegram_templates
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "005_product_expansion"
down_revision: str | None = "004_operacao_telegram_templates"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "operacoes",
        sa.Column("payment_provider", sa.String(length=32), server_default="asaas", nullable=False),
    )
    op.add_column(
        "operacoes",
        sa.Column("mercadopago_access_token", sa.String(length=512), nullable=True),
    )
    op.add_column("contratos", sa.Column("ultima_cobranca_telegram_em", sa.Date(), nullable=True))
    op.add_column(
        "contratos",
        sa.Column("mercadopago_subscription_id", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "cobrancas",
        sa.Column("payment_gateway", sa.String(length=32), server_default="asaas", nullable=False),
    )
    op.add_column(
        "cobrancas",
        sa.Column("mercadopago_payment_id", sa.String(length=64), nullable=True),
    )
    op.create_index(
        op.f("ix_cobrancas_mercadopago_payment_id"),
        "cobrancas",
        ["mercadopago_payment_id"],
        unique=False,
    )
    op.add_column(
        "usuarios",
        sa.Column(
            "cliente_id",
            sa.BigInteger(),
            sa.ForeignKey("clientes.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("usuarios", "cliente_id")
    op.drop_index(op.f("ix_cobrancas_mercadopago_payment_id"), table_name="cobrancas")
    op.drop_column("cobrancas", "mercadopago_payment_id")
    op.drop_column("cobrancas", "payment_gateway")
    op.drop_column("contratos", "mercadopago_subscription_id")
    op.drop_column("contratos", "ultima_cobranca_telegram_em")
    op.drop_column("operacoes", "mercadopago_access_token")
    op.drop_column("operacoes", "payment_provider")
