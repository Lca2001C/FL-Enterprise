"""add default contato bot menu button

Revision ID: 013_default_contato_button
Revises: 012_telegram_owner_notify
Create Date: 2026-05-27

"""

from __future__ import annotations

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "013_default_contato_button"
down_revision: str | None = "012_telegram_owner_notify"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CONTACT_BUTTON = {
    "label": "Quero falar com alguém",
    "command": "contato",
    "response": "Entendido, {cliente}. Nossa equipe entrará em contato em breve.",
}


def upgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(
        sa.text("SELECT id, telegram_bot_menu_buttons FROM operacoes")
    ).fetchall()
    for row_id, buttons in rows:
        if not buttons:
            continue
        if any(str(b.get("command", "")).lower() == "contato" for b in buttons):
            continue
        if len(buttons) >= 6:
            continue
        updated = [*buttons, _CONTACT_BUTTON]
        conn.execute(
            sa.text(
                "UPDATE operacoes SET telegram_bot_menu_buttons = CAST(:buttons AS jsonb) "
                "WHERE id = :id"
            ),
            {"buttons": json.dumps(updated), "id": row_id},
        )


def downgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(
        sa.text("SELECT id, telegram_bot_menu_buttons FROM operacoes")
    ).fetchall()
    for row_id, buttons in rows:
        if not buttons:
            continue
        updated = [b for b in buttons if str(b.get("command", "")).lower() != "contato"]
        if updated == buttons:
            continue
        conn.execute(
            sa.text(
                "UPDATE operacoes SET telegram_bot_menu_buttons = CAST(:buttons AS jsonb) "
                "WHERE id = :id"
            ),
            {"buttons": json.dumps(updated), "id": row_id},
        )
