"""módulo de manutenções + categoria no financeiro

Revision ID: 029_manutencoes
Revises: 028_multas_moto_data_idx
Create Date: 2026-07-02

Cria a tabela manutencoes (controle de serviços de manutenção por veículo,
espelhando a planilha de referência: veículo, tipo, descrição, causa, valor,
data do serviço e km) e a coluna financeiro.categoria, usada para marcar
despesas geradas automaticamente pelo módulo de manutenções.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "029_manutencoes"
down_revision: str | None = "028_multas_moto_data_idx"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "manutencoes",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("operacao_id", sa.BigInteger(), nullable=False),
        sa.Column("moto_id", sa.BigInteger(), nullable=False),
        sa.Column("tipo", sa.String(length=16), nullable=False),
        sa.Column("descricao", sa.String(length=512), nullable=False),
        sa.Column("causa", sa.String(length=16), nullable=False),
        sa.Column("valor", sa.Numeric(14, 2), nullable=False),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("km", sa.BigInteger(), nullable=True),
        sa.Column("financeiro_id", sa.BigInteger(), nullable=True),
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
        sa.ForeignKeyConstraint(["operacao_id"], ["operacoes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["moto_id"], ["motos.id"]),
        sa.ForeignKeyConstraint(["financeiro_id"], ["financeiro.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_manutencoes_operacao_id", "manutencoes", ["operacao_id"])
    op.create_index("ix_manutencoes_moto_id", "manutencoes", ["moto_id"])
    op.create_index("ix_manutencoes_tipo", "manutencoes", ["tipo"])
    op.create_index("ix_manutencoes_causa", "manutencoes", ["causa"])
    op.create_index("ix_manutencoes_data", "manutencoes", ["data"])
    op.create_index("ix_manutencoes_moto_data", "manutencoes", ["moto_id", "data"])

    op.add_column("financeiro", sa.Column("categoria", sa.String(length=32), nullable=True))
    op.create_index("ix_financeiro_categoria", "financeiro", ["categoria"])


def downgrade() -> None:
    op.drop_index("ix_financeiro_categoria", table_name="financeiro")
    op.drop_column("financeiro", "categoria")
    op.drop_index("ix_manutencoes_moto_data", table_name="manutencoes")
    op.drop_index("ix_manutencoes_data", table_name="manutencoes")
    op.drop_index("ix_manutencoes_causa", table_name="manutencoes")
    op.drop_index("ix_manutencoes_tipo", table_name="manutencoes")
    op.drop_index("ix_manutencoes_moto_id", table_name="manutencoes")
    op.drop_index("ix_manutencoes_operacao_id", table_name="manutencoes")
    op.drop_table("manutencoes")
