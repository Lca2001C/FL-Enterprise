from __future__ import annotations

from motopay.config import get_settings
from tests.conftest import auth_header, login


def test_payments_config_dono(client, dono_user, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("MERCADOPAGO_CREDENTIALS_MODE", "production")
    monkeypatch.setenv("MERCADOPAGO_ACCESS_TOKEN", "mp-access")
    monkeypatch.setenv("MERCADOPAGO_PUBLIC_KEY", "APP_USR-public-test")
    monkeypatch.setenv("MERCADOPAGO_WEBHOOK_SECRET", "wh-secret")
    get_settings.cache_clear()

    tokens = login(client, dono_user.email, "donodono")
    response = client.get(
        "/api/v1/config/payments",
        headers=auth_header(tokens["access_token"]),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["mercadopago_configured"] is True
    assert data["mercadopago_public_key"] == "APP_USR-public-test"
    assert data["webhook_configured"] is True
    assert data["credentials_mode"] == "production"
    assert data["mercadopago_credentials_source"] == "global"
    assert data["mercadopago_credentials_complete"] is True
    assert "mercadopago_access_token" not in data
    assert data["webhook_url"].endswith("/webhooks/mercadopago")
    get_settings.cache_clear()


def test_payments_config_returns_test_mode(client, dono_user, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("MERCADOPAGO_CREDENTIALS_MODE", "test")
    monkeypatch.setenv("MERCADOPAGO_ACCESS_TOKEN", "prod-token")
    monkeypatch.setenv("MERCADOPAGO_ACCESS_TOKEN_TEST", "test-token")
    monkeypatch.setenv("MERCADOPAGO_PUBLIC_KEY_TEST", "TEST-public")
    get_settings.cache_clear()

    tokens = login(client, dono_user.email, "donodono")
    response = client.get(
        "/api/v1/config/payments",
        headers=auth_header(tokens["access_token"]),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["credentials_mode"] == "test"
    assert data["mercadopago_public_key"] == "TEST-public"
    assert data["mercadopago_configured"] is True
    get_settings.cache_clear()


def test_payments_config_admin_partial_operacao_credentials(
    client, admin_user, operacao_a, db_session, monkeypatch
):
    monkeypatch.setenv("MERCADOPAGO_ACCESS_TOKEN", "")
    monkeypatch.setenv("MERCADOPAGO_PUBLIC_KEY", "")
    monkeypatch.setenv("MERCADOPAGO_WEBHOOK_SECRET", "")
    get_settings.cache_clear()

    operacao_a.mercadopago_access_token = "op-token"
    db_session.add(operacao_a)
    db_session.commit()

    tokens = login(client, admin_user.email, "adminadmin")
    response = client.get(
        f"/api/v1/config/payments?operacao_id={operacao_a.id}",
        headers=auth_header(tokens["access_token"]),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["mercadopago_configured"] is False
    assert data["mercadopago_credentials_complete"] is False
    assert data["mercadopago_has_operacao_token"] is True
    get_settings.cache_clear()


def test_payments_config_admin_full_operacao_credentials(
    client, admin_user, operacao_a, db_session, monkeypatch
):
    monkeypatch.setenv("MERCADOPAGO_ACCESS_TOKEN", "")
    monkeypatch.setenv("MERCADOPAGO_PUBLIC_KEY", "")
    monkeypatch.setenv("MERCADOPAGO_WEBHOOK_SECRET", "")
    get_settings.cache_clear()

    operacao_a.mercadopago_access_token = "op-token"
    operacao_a.mercadopago_public_key = "op-public"
    operacao_a.mercadopago_webhook_secret = "op-wh"
    db_session.add(operacao_a)
    db_session.commit()

    tokens = login(client, admin_user.email, "adminadmin")
    response = client.get(
        f"/api/v1/config/payments?operacao_id={operacao_a.id}",
        headers=auth_header(tokens["access_token"]),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["mercadopago_configured"] is True
    assert data["mercadopago_public_key"] == "op-public"
    assert data["webhook_configured"] is True
    assert data["mercadopago_credentials_source"] == "operacao"
    assert data["mercadopago_credentials_complete"] is True
    get_settings.cache_clear()
