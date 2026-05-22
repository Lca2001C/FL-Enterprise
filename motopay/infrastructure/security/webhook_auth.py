from __future__ import annotations

import secrets
from collections.abc import Mapping


def extract_webhook_token(
    *,
    query_token: str | None,
    headers: Mapping[str, str],
) -> str | None:
    """Prefere header para evitar token em logs de URL; query ainda suportado (Asaas)."""
    header_token = headers.get("x-webhook-token")
    if header_token and header_token.strip():
        return header_token.strip()
    if query_token and query_token.strip():
        return query_token.strip()
    return None


def verify_webhook_token(provided: str | None, expected: str) -> bool:
    if not provided or not expected:
        return False
    return secrets.compare_digest(provided, expected)
