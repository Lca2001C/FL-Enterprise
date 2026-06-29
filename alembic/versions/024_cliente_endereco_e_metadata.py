"""Cliente: endereço, sobrenome e created_at para MP compliance

Revision ID: 024_cliente_endereco
Revises: 023_moto_tipo_veiculo
Create Date: 2026-06-08

Adiciona campos requeridos pelas recomendações Mercado Pago para
melhoria da taxa de aprovação:
- sobrenome (preenchimento automático a partir do nome quando vazio)
- endereço (logradouro, número, bairro, cidade, estado/UF, CEP)
- created_at (registration_date para additional_info.payer)
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "024_cliente_endereco"
down_revision: str | None = "023_moto_tipo_veiculo"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "clientes",
        sa.Column("sobrenome", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "clientes",
        sa.Column("endereco_logradouro", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "clientes",
        sa.Column("endereco_numero", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "clientes",
        sa.Column("endereco_bairro", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "clientes",
        sa.Column("endereco_cidade", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "clientes",
        sa.Column("endereco_estado", sa.String(length=2), nullable=True),
    )
    op.add_column(
        "clientes",
        sa.Column("endereco_cep", sa.String(length=16), nullable=True),
    )
    op.add_column(
        "clientes",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_column("clientes", "created_at")
    op.drop_column("clientes", "endereco_cep")
    op.drop_column("clientes", "endereco_estado")
    op.drop_column("clientes", "endereco_cidade")
    op.drop_column("clientes", "endereco_bairro")
    op.drop_column("clientes", "endereco_numero")
    op.drop_column("clientes", "endereco_logradouro")
    op.drop_column("clientes", "sobrenome")
