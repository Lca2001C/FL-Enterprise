from __future__ import annotations

from tests.conftest import auth_header, login


def test_payments_config_reports_operacao_credentials(client, db_session, operacao_a, dono_user):
    token = login(client, "dono@test.local", "donodono")["access_token"]
    op = operacao_a
    # Formato válido exigido por operacao_mp_fields_complete (prefixo + tamanho).
    op.mercadopago_access_token = "TEST-1234567890123456-cfg"
    op.mercadopago_public_key = "TEST-pk-1234-5678-cfg"
    op.mercadopago_webhook_secret = "whsec-12345678"
    db_session.commit()

    r = client.get("/api/v1/config/payments", headers=auth_header(token))
    assert r.status_code == 200
    data = r.json()
    assert data["mercadopago_credentials_complete"] is True
    assert data["mercadopago_configured"] is True
    assert data["webhook_configured"] is True
    assert data["mercadopago_public_key"] == "TEST-pk-1234-5678-cfg"
    assert data["webhook_url"].endswith("/webhooks/mercadopago")
