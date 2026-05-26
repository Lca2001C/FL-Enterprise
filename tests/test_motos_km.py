from __future__ import annotations

from motopay.domain.enums import MotoStatus
from motopay.infrastructure.db.models import Usuario

from tests.conftest import auth_header, login


def test_create_moto_with_km(client, admin_user: Usuario, operacao_a):
    tokens = login(client, admin_user.email, "adminadmin")
    payload = {
        "placa": "KMZ4K44",
        "modelo": "Honda Pop 110i",
        "status": MotoStatus.DISPONIVEL.value,
        "km": 3500,
    }

    response = client.post(
        f"/api/v1/motos?operacao_id={operacao_a.id}",
        json=payload,
        headers=auth_header(tokens["access_token"]),
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["placa"] == "KMZ4K44"
    assert data["km"] == 3500


def test_update_moto_km(client, admin_user: Usuario, operacao_a, moto_operacao_a):
    tokens = login(client, admin_user.email, "adminadmin")
    patch_payload = {"km": 4200}

    response = client.patch(
        f"/api/v1/motos/{moto_operacao_a.id}?operacao_id={operacao_a.id}",
        json=patch_payload,
        headers=auth_header(tokens["access_token"]),
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["km"] == 4200
