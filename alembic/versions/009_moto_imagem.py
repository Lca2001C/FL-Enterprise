"""moto imagem path

Revision ID: 009_moto_imagem
Revises: 007_moto_km
Create Date: 2026-05-27

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "009_moto_imagem"
down_revision: str | None = "007_moto_km"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("motos", sa.Column("imagem_path", sa.String(length=512), nullable=True))


def downgrade() -> None:
    op.drop_column("motos", "imagem_path")
