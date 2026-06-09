"""Contrato: numero sequencial por operacao

Revision ID: 025_contrato_numero
Revises: 024_cliente_endereco
Create Date: 2026-06-08

Adiciona coluna `numero` à tabela contratos com numeração independente
por operação (1, 2, 3... reiniciando para cada operação).
Contratos existentes são retroativamente numerados em ordem de criação.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "025_contrato_numero"
down_revision: str | None = "024_cliente_endereco"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "contratos",
        sa.Column("numero", sa.BigInteger(), nullable=True),
    )
    op.create_index("ix_contratos_numero", "contratos", ["numero"])

    # Backfill: atribui numero sequencial por operacao, ordenado por id
    op.execute("""
        UPDATE contratos c
        SET numero = sub.rn
        FROM (
            SELECT id,
                   ROW_NUMBER() OVER (PARTITION BY operacao_id ORDER BY id) AS rn
            FROM contratos
        ) sub
        WHERE c.id = sub.id
    """)


def downgrade() -> None:
    op.drop_index("ix_contratos_numero", table_name="contratos")
    op.drop_column("contratos", "numero")
