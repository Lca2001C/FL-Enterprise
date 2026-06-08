from __future__ import annotations

from tests.conftest import auth_header, login


def test_payments_config_reports_operacao_credentials(client, db_session, operacao_a, dono_user):
    token = login(client, "dono@test.local", "donodono")["access_token"]
    op = operacao_a
    op.mercadopago_access_token = "TEST-token"
    op.mercadopago_public_key = "TEST-pk"
    op.mercadopago_webhook_secret = "whsec"
    db_session.commit()

    r = client.get("/api/v1/config/payments", headers=auth_header(token))
    assert r.status_code == 200
    data = r.json()
    assert data["mercadopago_credentials_complete"] is True
    assert data["mercadopago_configured"] is True
    assert data["webhook_configured"] is True
    assert data["mercadopago_public_key"] == "TEST-pk"
    assert data["webhook_url"].endswith("/webhooks/mercadopago")
