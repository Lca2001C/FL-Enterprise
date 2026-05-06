from __future__ import annotations

import os
from typing import Any

import httpx
import streamlit as st


def api_base() -> str:
    return str(st.session_state.get("api_base") or os.getenv("API_PUBLIC_BASE_URL", "http://localhost:8000")).rstrip(
        "/"
    )


def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {st.session_state['token']}"}


def query_operacao() -> dict[str, Any]:
    oid = st.session_state.get("operacao_id")
    if oid and int(oid) > 0:
        return {"operacao_id": int(oid)}
    return {}


def get_json(path: str, params: dict[str, Any] | None = None) -> Any:
    p = {**(params or {}), **query_operacao()}
    r = httpx.get(f"{api_base()}{path}", headers=auth_headers(), params=p, timeout=60.0)
    r.raise_for_status()
    return r.json()


def post_json(path: str, body: dict[str, Any]) -> Any:
    r = httpx.post(
        f"{api_base()}{path}",
        headers={**auth_headers(), "Content-Type": "application/json"},
        json=body,
        params=query_operacao(),
        timeout=60.0,
    )
    r.raise_for_status()
    return r.json() if r.content else {}
