from __future__ import annotations

import secrets
from collections.abc import Mapping


def extract_webhook_token(
    *,
    query_token: str | None,
    headers: Mapping[str, str],
) -> str | None:
    """Prefere header para evitar token em logs de URL; query suportado só em desenvolvimento."""
    header_token = headers.get("x-webhook-token")
    if header_token and header_token.strip():
        return header_token.strip()
    if query_token and query_token.strip():
        return query_token.strip()
    return None


def webhook_rejects_query_token(
    *,
    query_token: str | None,
    headers: Mapping[str, str],
    allow_query: bool,
) -> bool:
    """True quando produção recusa token exclusivamente na query string."""
    if allow_query:
        return False
    header_token = headers.get("x-webhook-token")
    if header_token and header_token.strip():
        return False
    return bool(query_token and query_token.strip())


def verify_webhook_token(provided: str | None, expected: str) -> bool:
    if not provided or not expected:
        return False
    return secrets.compare_digest(provided, expected)
