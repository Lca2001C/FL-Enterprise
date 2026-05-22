"""contrato data fim vigencia

Revision ID: 007_contrato_data_fim_vigencia
Revises: 006_admin_dono_only
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "007_contrato_data_fim_vigencia"
down_revision: str | None = "006_admin_dono_only"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("contratos", sa.Column("data_fim_vigencia", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("contratos", "data_fim_vigencia")
