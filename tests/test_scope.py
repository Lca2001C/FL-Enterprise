from __future__ import annotations

from motopay.infrastructure.db.models import Moto, Usuario

from tests.conftest import auth_header, login


def test_dono_cannot_see_other_operacao_moto(
    client,
    dono_user: Usuario,
    moto_operacao_a: Moto,
    moto_operacao_b: Moto,
):
    tokens = login(client, dono_user.email, "donodono")
    headers = auth_header(tokens["access_token"])

    own = client.get(f"/api/v1/motos/{moto_operacao_a.id}", headers=headers)
    assert own.status_code == 200

    other = client.get(f"/api/v1/motos/{moto_operacao_b.id}", headers=headers)
    assert other.status_code == 403


def test_admin_with_operacao_scope_filters_list(
    client,
    admin_user: Usuario,
    moto_operacao_a: Moto,
    moto_operacao_b: Moto,
):
    tokens = login(client, admin_user.email, "adminadmin")
    headers = auth_header(tokens["access_token"])

    scoped = client.get(
        "/api/v1/motos",
        headers=headers,
        params={"operacao_id": moto_operacao_a.operacao_id},
    )
    assert scoped.status_code == 200
    placas = {row["placa"] for row in scoped.json()["items"]}
    assert moto_operacao_a.placa in placas
    assert moto_operacao_b.placa not in placas
