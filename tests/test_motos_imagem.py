from __future__ import annotations

import io

import pytest
from motopay.config.settings import get_settings
from motopay.infrastructure.db.models import Usuario

from tests.conftest import auth_header, login

JPEG_BYTES = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    b"\xff\xd9"
)


@pytest.fixture
def upload_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


def test_upload_moto_imagem(
    client, admin_user: Usuario, operacao_a, moto_operacao_a, upload_dir
):
    tokens = login(client, admin_user.email, "adminadmin")
    response = client.post(
        f"/api/v1/motos/{moto_operacao_a.id}/imagem?operacao_id={operacao_a.id}",
        files={"file": ("moto.jpg", io.BytesIO(JPEG_BYTES), "image/jpeg")},
        headers=auth_header(tokens["access_token"]),
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["tem_imagem"] is True

    get_response = client.get(
        f"/api/v1/motos/{moto_operacao_a.id}/imagem?operacao_id={operacao_a.id}",
        headers=auth_header(tokens["access_token"]),
    )
    assert get_response.status_code == 200
    assert get_response.headers["content-type"].startswith("image/")


def test_get_moto_imagem_not_found(client, admin_user: Usuario, operacao_a, moto_operacao_a):
    tokens = login(client, admin_user.email, "adminadmin")
    response = client.get(
        f"/api/v1/motos/{moto_operacao_a.id}/imagem?operacao_id={operacao_a.id}",
        headers=auth_header(tokens["access_token"]),
    )
    assert response.status_code == 404


def test_delete_moto_imagem(
    client, admin_user: Usuario, operacao_a, moto_operacao_a, upload_dir
):
    tokens = login(client, admin_user.email, "adminadmin")
    headers = auth_header(tokens["access_token"])
    upload = client.post(
        f"/api/v1/motos/{moto_operacao_a.id}/imagem?operacao_id={operacao_a.id}",
        files={"file": ("moto.jpg", io.BytesIO(JPEG_BYTES), "image/jpeg")},
        headers=headers,
    )
    assert upload.status_code == 200

    delete = client.delete(
        f"/api/v1/motos/{moto_operacao_a.id}/imagem?operacao_id={operacao_a.id}",
        headers=headers,
    )
    assert delete.status_code == 200, delete.text
    assert delete.json()["tem_imagem"] is False

    get_response = client.get(
        f"/api/v1/motos/{moto_operacao_a.id}/imagem?operacao_id={operacao_a.id}",
        headers=headers,
    )
    assert get_response.status_code == 404


def test_upload_moto_imagem_invalid_type(
    client, admin_user: Usuario, operacao_a, moto_operacao_a, upload_dir
):
    tokens = login(client, admin_user.email, "adminadmin")
    response = client.post(
        f"/api/v1/motos/{moto_operacao_a.id}/imagem?operacao_id={operacao_a.id}",
        files={"file": ("nota.txt", io.BytesIO(b"hello"), "text/plain")},
        headers=auth_header(tokens["access_token"]),
    )
    assert response.status_code == 400
