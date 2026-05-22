from __future__ import annotations

from motopay.domain.enums import UserRole
from motopay.infrastructure.db.models import Usuario

from tests.conftest import auth_header, login


def test_list_usuarios_admin(client, admin_user: Usuario, dono_user: Usuario):
    tokens = login(client, admin_user.email, "adminadmin")
    response = client.get(
        "/api/v1/usuarios",
        headers=auth_header(tokens["access_token"]),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 2
    assert len(data["items"]) >= 2
    emails = {item["email"] for item in data["items"]}
    assert admin_user.email in emails
    assert dono_user.email in emails
    dono_row = next(i for i in data["items"] if i["email"] == dono_user.email)
    assert dono_row["tipo"] == UserRole.DONO.value
    assert dono_row["operacao_nome"] is not None
    assert "created_at" in dono_row


def test_list_usuarios_filter_tipo(client, admin_user: Usuario, dono_user: Usuario):
    tokens = login(client, admin_user.email, "adminadmin")
    response = client.get(
        "/api/v1/usuarios",
        params={"tipo": UserRole.DONO.value},
        headers=auth_header(tokens["access_token"]),
    )
    assert response.status_code == 200
    data = response.json()
    assert all(item["tipo"] == UserRole.DONO.value for item in data["items"])
    assert any(item["email"] == dono_user.email for item in data["items"])


def test_list_usuarios_forbidden_for_dono(client, dono_user: Usuario):
    tokens = login(client, dono_user.email, "donodono")
    response = client.get(
        "/api/v1/usuarios",
        headers=auth_header(tokens["access_token"]),
    )
    assert response.status_code == 403
