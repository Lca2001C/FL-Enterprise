"""admin and dono login roles only

Revision ID: 006_admin_dono_only
Revises: 005_product_expansion
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "006_admin_dono_only"
down_revision: str | None = "005_product_expansion"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(sa.text("DELETE FROM usuarios WHERE tipo IN ('operador', 'cliente')"))
    op.drop_column("usuarios", "cliente_id")


def downgrade() -> None:
    op.add_column(
        "usuarios",
        sa.Column(
            "cliente_id",
            sa.BigInteger(),
            sa.ForeignKey("clientes.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
