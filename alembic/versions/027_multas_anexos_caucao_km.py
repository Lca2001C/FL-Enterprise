"""multas, anexos, caucao/km no contrato e ano/cor na moto

Revision ID: 027_multas_anexos
Revises: 026_mp_tenant_oauth
Create Date: 2026-06-29

- Adiciona ano/cor à tabela motos.
- Adiciona valor_caucao, km_entrega e km_devolucao à tabela contratos.
- Cria a tabela multas (multas de trânsito por veículo/contrato).
- Cria a tabela anexos (PDF/fotos genéricos por entidade: multa, financeiro).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "027_multas_anexos"
down_revision: str | None = "026_mp_tenant_oauth"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Moto: ano e cor
    op.add_column("motos", sa.Column("ano", sa.BigInteger(), nullable=True))
    op.add_column("motos", sa.Column("cor", sa.String(length=32), nullable=True))

    # Contrato: caução e quilometragem de entrega/devolução
    op.add_column(
        "contratos",
        sa.Column("valor_caucao", sa.Numeric(14, 2), nullable=False, server_default="0"),
    )
    op.add_column("contratos", sa.Column("km_entrega", sa.BigInteger(), nullable=True))
    op.add_column("contratos", sa.Column("km_devolucao", sa.BigInteger(), nullable=True))

    # Multas
    op.create_table(
        "multas",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("operacao_id", sa.BigInteger(), nullable=False),
        sa.Column("moto_id", sa.BigInteger(), nullable=False),
        sa.Column("contrato_id", sa.BigInteger(), nullable=True),
        sa.Column("cliente_id", sa.BigInteger(), nullable=True),
        sa.Column("descricao", sa.String(length=512), nullable=False),
        sa.Column("orgao", sa.String(length=128), nullable=True),
        sa.Column("valor", sa.Numeric(14, 2), nullable=False),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("vencimento", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pendente"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["operacao_id"], ["operacoes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["moto_id"], ["motos.id"]),
        sa.ForeignKeyConstraint(["contrato_id"], ["contratos.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["cliente_id"], ["clientes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_multas_operacao_id", "multas", ["operacao_id"])
    op.create_index("ix_multas_data", "multas", ["data"])
    op.create_index("ix_multas_status", "multas", ["status"])

    # Anexos genéricos
    op.create_table(
        "anexos",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("operacao_id", sa.BigInteger(), nullable=False),
        sa.Column("entidade_tipo", sa.String(length=32), nullable=False),
        sa.Column("entidade_id", sa.BigInteger(), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("tamanho", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["operacao_id"], ["operacoes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_anexos_operacao_id", "anexos", ["operacao_id"])
    op.create_index("ix_anexos_entidade_tipo", "anexos", ["entidade_tipo"])
    op.create_index("ix_anexos_entidade_id", "anexos", ["entidade_id"])


def downgrade() -> None:
    op.drop_index("ix_anexos_entidade_id", table_name="anexos")
    op.drop_index("ix_anexos_entidade_tipo", table_name="anexos")
    op.drop_index("ix_anexos_operacao_id", table_name="anexos")
    op.drop_table("anexos")

    op.drop_index("ix_multas_status", table_name="multas")
    op.drop_index("ix_multas_data", table_name="multas")
    op.drop_index("ix_multas_operacao_id", table_name="multas")
    op.drop_table("multas")

    op.drop_column("contratos", "km_devolucao")
    op.drop_column("contratos", "km_entrega")
    op.drop_column("contratos", "valor_caucao")

    op.drop_column("motos", "cor")
    op.drop_column("motos", "ano")
