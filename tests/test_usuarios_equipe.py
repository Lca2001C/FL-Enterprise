"""Equipe da operação: DONO adiciona/lista usuários da própria operação."""

from __future__ import annotations

from motopay.domain.enums import UserRole
from motopay.infrastructure.db.models import Usuario
from sqlalchemy import select

from tests.conftest import auth_header, login


def test_dono_adds_user_to_own_operacao(client, db_session, dono_user, operacao_a):
    token = login(client, "dono@test.local", "donodono")["access_token"]
    r = client.post(
        "/api/v1/usuarios/equipe",
        json={"email": "novo@example.com", "password": "senhaforte1"},
        headers=auth_header(token),
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["email"] == "novo@example.com"
    assert data["tipo"] == "dono"
    assert data["operacao_id"] == operacao_a.id

    created = db_session.scalars(
        select(Usuario).where(Usuario.email == "novo@example.com")
    ).first()
    assert created is not None


def test_dono_equipe_list_only_own_operacao(
    client, db_session, dono_user, operacao_a, operacao_b
):
    # Usuário de outra operação não deve aparecer na lista da equipe.
    from motopay.services.auth_service import hash_password

    other = Usuario(
        email="outro@test.local",
        senha_hash=hash_password("outrasenha1"),
        tipo=UserRole.DONO.value,
        operacao_id=operacao_b.id,
    )
    db_session.add(other)
    db_session.flush()

    token = login(client, "dono@test.local", "donodono")["access_token"]
    r = client.get("/api/v1/usuarios/equipe", headers=auth_header(token))
    assert r.status_code == 200, r.text
    emails = {item["email"] for item in r.json()["items"]}
    assert "dono@test.local" in emails
    assert "outro@test.local" not in emails


def test_dono_cannot_target_other_operacao(client, dono_user, operacao_a, operacao_b):
    # DONO tentando passar operacao_id de outra operação: resolve_operacao_id ignora
    # o query param para DONO, então o usuário cai SEMPRE na operação do token.
    token = login(client, "dono@test.local", "donodono")["access_token"]
    r = client.post(
        f"/api/v1/usuarios/equipe?operacao_id={operacao_b.id}",
        json={"email": "intruso@example.com", "password": "senhaforte1"},
        headers=auth_header(token),
    )
    assert r.status_code == 200, r.text
    assert r.json()["operacao_id"] == operacao_a.id  # não a operacao_b


def test_equipe_duplicate_email_conflict(client, dono_user):
    token = login(client, "dono@test.local", "donodono")["access_token"]
    payload = {"email": "dup@example.com", "password": "senhaforte1"}
    first = client.post("/api/v1/usuarios/equipe", json=payload, headers=auth_header(token))
    assert first.status_code == 200, first.text
    again = client.post("/api/v1/usuarios/equipe", json=payload, headers=auth_header(token))
    assert again.status_code == 409, again.text


def test_admin_adds_user_with_operacao_scope(client, admin_user, operacao_a):
    token = login(client, "admin@test.local", "adminadmin")["access_token"]
    r = client.post(
        f"/api/v1/usuarios/equipe?operacao_id={operacao_a.id}",
        json={"email": "viaadmin@example.com", "password": "senhaforte1"},
        headers=auth_header(token),
    )
    assert r.status_code == 200, r.text
    assert r.json()["operacao_id"] == operacao_a.id


def test_equipe_requires_auth(client):
    r = client.get("/api/v1/usuarios/equipe")
    assert r.status_code in (401, 403)
