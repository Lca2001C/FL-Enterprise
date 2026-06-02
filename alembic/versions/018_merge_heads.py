"""merge alembic heads (017 + 009_mercadopago_only)

Revision ID: 018_merge_heads
Revises: 017_mercadopago_order_id, 009_mercadopago_only
Create Date: 2026-06-01

"""

from __future__ import annotations

from collections.abc import Sequence

revision: str = "018_merge_heads"
down_revision: str | tuple[str, ...] | None = (
    "017_mercadopago_order_id",
    "009_mercadopago_only",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
