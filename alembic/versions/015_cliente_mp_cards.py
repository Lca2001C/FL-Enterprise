"""cliente mercadopago customer and saved cards

Revision ID: 015_cliente_mp_cards
Revises: 014_operacao_mercadopago_full
Create Date: 2026-06-02

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "015_cliente_mp_cards"
down_revision: str | None = "014_operacao_mercadopago_full"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "clientes",
        sa.Column("mercadopago_customer_id", sa.String(length=64), nullable=True),
    )
    op.create_index("ix_clientes_mercadopago_customer_id", "clientes", ["mercadopago_customer_id"])

    op.create_table(
        "cliente_mp_cards",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("cliente_id", sa.BigInteger(), nullable=False),
        sa.Column("operacao_id", sa.BigInteger(), nullable=False),
        sa.Column("mp_card_id", sa.String(length=64), nullable=False),
        sa.Column("payment_method_id", sa.String(length=32), nullable=False),
        sa.Column("last_four_digits", sa.String(length=4), nullable=False),
        sa.Column("cardholder_name", sa.String(length=255), nullable=True),
        sa.Column("expiration_month", sa.Integer(), nullable=True),
        sa.Column("expiration_year", sa.Integer(), nullable=True),
        sa.Column("is_default", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["cliente_id"], ["clientes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["operacao_id"], ["operacoes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cliente_id", "mp_card_id", name="uq_cliente_mp_cards_cliente_mp_card"),
    )
    op.create_index("ix_cliente_mp_cards_cliente_id", "cliente_mp_cards", ["cliente_id"])
    op.create_index("ix_cliente_mp_cards_operacao_id", "cliente_mp_cards", ["operacao_id"])


def downgrade() -> None:
    op.drop_index("ix_cliente_mp_cards_operacao_id", table_name="cliente_mp_cards")
    op.drop_index("ix_cliente_mp_cards_cliente_id", table_name="cliente_mp_cards")
    op.drop_table("cliente_mp_cards")
    op.drop_index("ix_clientes_mercadopago_customer_id", table_name="clientes")
    op.drop_column("clientes", "mercadopago_customer_id")
