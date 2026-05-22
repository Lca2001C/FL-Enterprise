"""initial schema

Revision ID: 001_initial
Revises:
Create Date: 2026-05-06

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "operacoes",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("nome", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "usuarios",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("senha_hash", sa.String(length=255), nullable=False),
        sa.Column("tipo", sa.String(length=32), nullable=False),
        sa.Column("operacao_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["operacao_id"], ["operacoes.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_usuarios_email"), "usuarios", ["email"], unique=True)
    op.create_index(op.f("ix_usuarios_tipo"), "usuarios", ["tipo"], unique=False)

    op.create_table(
        "motos",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("operacao_id", sa.BigInteger(), nullable=False),
        sa.Column("placa", sa.String(length=16), nullable=False),
        sa.Column("modelo", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["operacao_id"], ["operacoes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("operacao_id", "placa", name="uq_motos_operacao_placa"),
    )
    op.create_index(op.f("ix_motos_operacao_id"), "motos", ["operacao_id"], unique=False)
    op.create_index(op.f("ix_motos_status"), "motos", ["status"], unique=False)

    op.create_table(
        "clientes",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("operacao_id", sa.BigInteger(), nullable=False),
        sa.Column("nome", sa.String(length=255), nullable=False),
        sa.Column("cpf", sa.String(length=14), nullable=False),
        sa.Column("telefone", sa.String(length=32), nullable=False),
        sa.Column("telegram_id", sa.String(length=64), nullable=True),
        sa.Column("score", sa.BigInteger(), server_default="100", nullable=False),
        sa.ForeignKeyConstraint(["operacao_id"], ["operacoes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("operacao_id", "cpf", name="uq_clientes_operacao_cpf"),
    )
    op.create_index(op.f("ix_clientes_operacao_id"), "clientes", ["operacao_id"], unique=False)
    op.create_index(op.f("ix_clientes_telegram_id"), "clientes", ["telegram_id"], unique=False)

    op.create_table(
        "contratos",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("operacao_id", sa.BigInteger(), nullable=False),
        sa.Column("cliente_id", sa.BigInteger(), nullable=False),
        sa.Column("moto_id", sa.BigInteger(), nullable=False),
        sa.Column("valor_recorrente", sa.Numeric(14, 2), nullable=False),
        sa.Column("ciclo", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("data_inicio", sa.Date(), nullable=False),
        sa.Column("proximo_vencimento", sa.Date(), nullable=False),
        sa.Column(
            "nivel_escalonamento_cobranca", sa.BigInteger(), server_default="0", nullable=False
        ),
        sa.Column("dias_atraso_acumulado", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("inadimplente", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("asaas_customer_id", sa.String(length=64), nullable=True),
        sa.Column("asaas_subscription_id", sa.String(length=64), nullable=True),
        sa.Column("promessa_pagamento_em", sa.Date(), nullable=True),
        sa.Column("promessa_notas", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["cliente_id"], ["clientes.id"]),
        sa.ForeignKeyConstraint(["moto_id"], ["motos.id"]),
        sa.ForeignKeyConstraint(["operacao_id"], ["operacoes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_contratos_operacao_id"), "contratos", ["operacao_id"], unique=False)
    op.create_index(
        op.f("ix_contratos_proximo_vencimento"), "contratos", ["proximo_vencimento"], unique=False
    )
    op.create_index(op.f("ix_contratos_status"), "contratos", ["status"], unique=False)

    op.create_table(
        "financeiro",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("operacao_id", sa.BigInteger(), nullable=False),
        sa.Column("tipo", sa.String(length=16), nullable=False),
        sa.Column("valor", sa.Numeric(14, 2), nullable=False),
        sa.Column("descricao", sa.String(length=512), nullable=False),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("moto_id", sa.BigInteger(), nullable=True),
        sa.Column("contrato_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["contrato_id"], ["contratos.id"]),
        sa.ForeignKeyConstraint(["moto_id"], ["motos.id"]),
        sa.ForeignKeyConstraint(["operacao_id"], ["operacoes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_financeiro_data"), "financeiro", ["data"], unique=False)
    op.create_index(op.f("ix_financeiro_operacao_id"), "financeiro", ["operacao_id"], unique=False)
    op.create_index(op.f("ix_financeiro_tipo"), "financeiro", ["tipo"], unique=False)

    op.create_table(
        "cobrancas",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("operacao_id", sa.BigInteger(), nullable=False),
        sa.Column("contrato_id", sa.BigInteger(), nullable=False),
        sa.Column("valor", sa.Numeric(14, 2), nullable=False),
        sa.Column("vencimento", sa.Date(), nullable=False),
        sa.Column("asaas_payment_id", sa.String(length=64), nullable=True),
        sa.Column("pix_copia_cola", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["contrato_id"], ["contratos.id"]),
        sa.ForeignKeyConstraint(["operacao_id"], ["operacoes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asaas_payment_id"),
    )
    op.create_index(op.f("ix_cobrancas_operacao_id"), "cobrancas", ["operacao_id"], unique=False)
    op.create_index(op.f("ix_cobrancas_status"), "cobrancas", ["status"], unique=False)

    op.create_table(
        "eventos_dominio",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tipo", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("processado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_eventos_dominio_tipo"), "eventos_dominio", ["tipo"], unique=False)


def downgrade() -> None:
    op.drop_table("eventos_dominio")
    op.drop_table("cobrancas")
    op.drop_table("financeiro")
    op.drop_table("contratos")
    op.drop_table("clientes")
    op.drop_table("motos")
    op.drop_table("usuarios")
    op.drop_table("operacoes")
