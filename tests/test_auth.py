from __future__ import annotations

from motopay.infrastructure.db.models import Usuario

from tests.conftest import auth_header, login


def test_login_returns_access_and_refresh(client, admin_user: Usuario):
    data = login(client, admin_user.email, "adminadmin")
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_credentials(client, admin_user: Usuario):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": admin_user.email, "password": "wrong-password"},
    )
    assert response.status_code == 401


def test_refresh_rotates_token(client, admin_user: Usuario):
    first = login(client, admin_user.email, "adminadmin")
    refresh_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": first["refresh_token"]},
    )
    assert refresh_response.status_code == 200
    second = refresh_response.json()
    assert second["access_token"]
    assert second["refresh_token"] != first["refresh_token"]

    stale = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": first["refresh_token"]},
    )
    assert stale.status_code == 401


def test_logout_revokes_refresh_token(client, admin_user: Usuario):
    tokens = login(client, admin_user.email, "adminadmin")
    logout = client.post("/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    assert logout.status_code == 200

    refresh = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refresh.status_code == 401


def test_me_requires_bearer(client, admin_user: Usuario):
    tokens = login(client, admin_user.email, "adminadmin")
    ok = client.get("/api/v1/auth/me", headers=auth_header(tokens["access_token"]))
    assert ok.status_code == 200
    assert ok.json()["email"] == admin_user.email

    unauthorized = client.get("/api/v1/auth/me")
    assert unauthorized.status_code == 401
