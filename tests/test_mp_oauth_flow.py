"""Fluxo OAuth Mercado Pago: start → callback (state single-use) → disconnect."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import pytest
from motopay.config import get_settings
from motopay.infrastructure.db.models import Operacao
from motopay.services.mercadopago_token_service import refresh_expiring_mp_oauth_tokens

from tests.conftest import auth_header, login

# Formato real do MP: prefixo APP_USR-/TEST- e ≥20 chars (is_valid_mp_access_token).
_OAUTH_TOKEN = "APP_USR-1111111111111111-oauth"
_OAUTH_PUBLIC_KEY = "APP_USR-pk-1234-5678-oauth"

_EXCHANGE_OK = {
    "access_token": _OAUTH_TOKEN,
    "refresh_token": "TG-refresh-abc",
    "public_key": _OAUTH_PUBLIC_KEY,
    "user_id": 987654321,
    "expires_in": 15552000,  # ~180 dias
}


@pytest.fixture
def oauth_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("MERCADOPAGO_OAUTH_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("MERCADOPAGO_OAUTH_CLIENT_SECRET", "test-client-secret")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _start_and_get_state(client, token: str) -> str:
    r = client.get("/api/v1/operacoes/mp-oauth/start", headers=auth_header(token))
    assert r.status_code == 200, r.text
    url = r.json()["authorization_url"]
    return parse_qs(urlparse(url).query)["state"][0]


def test_oauth_start_returns_authorization_url(client, oauth_env, dono_user):
    token = login(client, "dono@test.local", "donodono")["access_token"]
    r = client.get("/api/v1/operacoes/mp-oauth/start", headers=auth_header(token))
    assert r.status_code == 200, r.text
    data = r.json()
    url = data["authorization_url"]
    assert url.startswith("https://auth.mercadopago.com/authorization?")
    q = parse_qs(urlparse(url).query)
    assert q["client_id"] == ["test-client-id"]
    assert q["response_type"] == ["code"]
    assert q["state"][0]
    assert q["redirect_uri"][0].endswith("/api/v1/operacoes/mp-oauth/callback")
    assert data["redirect_uri"].endswith("/api/v1/operacoes/mp-oauth/callback")


def test_oauth_callback_persists_tokens(client, oauth_env, db_session, dono_user, operacao_a):
    token = login(client, "dono@test.local", "donodono")["access_token"]
    state = _start_and_get_state(client, token)
    with patch(
        "motopay.services.mercadopago_oauth_service.exchange_oauth_code",
        return_value=dict(_EXCHANGE_OK),
    ):
        r = client.get(
            "/api/v1/operacoes/mp-oauth/callback",
            params={"code": "auth-code-1", "state": state},
            follow_redirects=False,
        )
    assert r.status_code == 302
    location = r.headers["location"]
    assert "/ajustes?" in location
    assert "mp_oauth=ok" in location

    db_session.refresh(operacao_a)
    assert operacao_a.mercadopago_access_token == _OAUTH_TOKEN
    assert operacao_a.mercadopago_public_key == _OAUTH_PUBLIC_KEY
    assert operacao_a.mercadopago_refresh_token == "TG-refresh-abc"
    assert operacao_a.mercadopago_oauth_user_id == "987654321"
    assert operacao_a.mercadopago_oauth_expires_at is not None


def test_oauth_callback_rejects_invalid_state(client, oauth_env):
    r = client.get(
        "/api/v1/operacoes/mp-oauth/callback",
        params={"code": "auth-code-1", "state": "state-forjado"},
        follow_redirects=False,
    )
    assert r.status_code == 302
    assert "mp_oauth=error" in r.headers["location"]


def test_oauth_callback_rejects_replayed_state(client, oauth_env, dono_user):
    token = login(client, "dono@test.local", "donodono")["access_token"]
    state = _start_and_get_state(client, token)
    with patch(
        "motopay.services.mercadopago_oauth_service.exchange_oauth_code",
        return_value=dict(_EXCHANGE_OK),
    ):
        first = client.get(
            "/api/v1/operacoes/mp-oauth/callback",
            params={"code": "auth-code-1", "state": state},
            follow_redirects=False,
        )
        replay = client.get(
            "/api/v1/operacoes/mp-oauth/callback",
            params={"code": "auth-code-2", "state": state},
            follow_redirects=False,
        )
    assert "mp_oauth=ok" in first.headers["location"]
    assert "mp_oauth=error" in replay.headers["location"]
    assert "utilizado" in replay.headers["location"]


def test_oauth_callback_with_provider_error(client, oauth_env):
    r = client.get(
        "/api/v1/operacoes/mp-oauth/callback",
        params={"error": "access_denied"},
        follow_redirects=False,
    )
    assert r.status_code == 302
    assert "mp_oauth=error" in r.headers["location"]


def test_oauth_disconnect_clears_columns(client, oauth_env, db_session, dono_user, operacao_a):
    operacao_a.mercadopago_access_token = _OAUTH_TOKEN
    operacao_a.mercadopago_refresh_token = "TG-refresh-abc"
    operacao_a.mercadopago_oauth_user_id = "987654321"
    operacao_a.mercadopago_oauth_expires_at = datetime.now(UTC) + timedelta(days=90)
    db_session.add(operacao_a)
    db_session.flush()

    token = login(client, "dono@test.local", "donodono")["access_token"]
    r = client.post("/api/v1/operacoes/mp-oauth/disconnect", headers=auth_header(token))
    assert r.status_code == 200
    assert r.json() == {"ok": True}

    db_session.refresh(operacao_a)
    assert operacao_a.mercadopago_access_token is None
    assert operacao_a.mercadopago_refresh_token is None
    assert operacao_a.mercadopago_oauth_user_id is None
    assert operacao_a.mercadopago_oauth_expires_at is None


def test_refresh_expiring_tokens_only_within_window(db_session):
    new_token = "APP_USR-2222222222222222-new"
    expiring = Operacao(
        nome="Op Expirando",
        mercadopago_access_token=_OAUTH_TOKEN,
        mercadopago_public_key=_OAUTH_PUBLIC_KEY,
        mercadopago_refresh_token="TG-refresh-old",
        mercadopago_oauth_expires_at=datetime.now(UTC) + timedelta(days=3),
    )
    healthy = Operacao(
        nome="Op Saudável",
        mercadopago_access_token=_OAUTH_TOKEN,
        mercadopago_public_key=_OAUTH_PUBLIC_KEY,
        mercadopago_refresh_token="TG-refresh-ok",
        mercadopago_oauth_expires_at=datetime.now(UTC) + timedelta(days=30),
    )
    db_session.add_all([expiring, healthy])
    db_session.commit()

    with patch(
        "motopay.services.mercadopago_token_service.refresh_oauth_token",
        return_value={
            "access_token": new_token,
            "refresh_token": "TG-refresh-rotated",
            "expires_in": 15552000,
        },
    ) as refresh_mock:
        refreshed = refresh_expiring_mp_oauth_tokens(db_session)

    assert refreshed == 1
    refresh_mock.assert_called_once_with(refresh_token="TG-refresh-old")
    db_session.refresh(expiring)
    db_session.refresh(healthy)
    assert expiring.mercadopago_access_token == new_token
    assert expiring.mercadopago_refresh_token == "TG-refresh-rotated"
    assert healthy.mercadopago_access_token == _OAUTH_TOKEN
    assert healthy.mercadopago_refresh_token == "TG-refresh-ok"
