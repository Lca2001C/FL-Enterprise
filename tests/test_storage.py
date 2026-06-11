"""Camada de storage de objetos: backend local, backend S3 (mock) e fábrica."""

from __future__ import annotations

import io
from unittest.mock import MagicMock, patch

import pytest
from motopay.config.settings import Settings, get_settings
from motopay.domain.exceptions import MotoPayError
from motopay.infrastructure.storage import get_storage
from motopay.infrastructure.storage.local import LocalStorage
from motopay.infrastructure.storage.s3 import S3Storage

# --- LocalStorage -----------------------------------------------------------


def test_local_storage_save_read_delete(tmp_path):
    s = LocalStorage(tmp_path)
    assert s.exists("motos/1/2.jpg") is False
    assert s.read("motos/1/2.jpg") is None

    s.save("motos/1/2.jpg", b"abc", "image/jpeg")
    assert s.exists("motos/1/2.jpg") is True
    assert s.read("motos/1/2.jpg") == b"abc"

    s.delete("motos/1/2.jpg")
    assert s.exists("motos/1/2.jpg") is False
    s.delete("motos/1/2.jpg")  # idempotente


def test_local_storage_blocks_path_traversal(tmp_path):
    s = LocalStorage(tmp_path)
    with pytest.raises(MotoPayError):
        s.save("../escape.jpg", b"x", "image/jpeg")


# --- Fábrica get_storage ----------------------------------------------------


def test_get_storage_defaults_to_local(monkeypatch, tmp_path):
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    get_settings.cache_clear()
    try:
        assert isinstance(get_storage(), LocalStorage)
    finally:
        get_settings.cache_clear()


def test_get_storage_builds_s3(monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "s3")
    monkeypatch.setenv("S3_BUCKET", "motopay-test")
    monkeypatch.setenv("S3_ACCESS_KEY_ID", "AKIA-test")
    monkeypatch.setenv("S3_SECRET_ACCESS_KEY", "secret-test")
    get_settings.cache_clear()
    try:
        with patch("boto3.client", return_value=MagicMock()) as mk:
            storage = get_storage()
        assert isinstance(storage, S3Storage)
        mk.assert_called_once()
    finally:
        get_settings.cache_clear()


# --- Validação de settings --------------------------------------------------


def test_settings_rejects_invalid_storage_backend(monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "ftp")
    with pytest.raises(RuntimeError, match="STORAGE_BACKEND"):
        Settings()


def test_settings_s3_requires_bucket_and_keys(monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "s3")
    monkeypatch.delenv("S3_BUCKET", raising=False)
    monkeypatch.delenv("S3_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("S3_SECRET_ACCESS_KEY", raising=False)
    with pytest.raises(RuntimeError, match="S3_BUCKET"):
        Settings()


# --- S3Storage (boto3 mockado) ----------------------------------------------


def _s3_with_mock_client() -> tuple[S3Storage, MagicMock]:
    client = MagicMock()
    with patch("boto3.client", return_value=client):
        storage = S3Storage(
            bucket="motopay-test",
            endpoint_url="https://acct.r2.cloudflarestorage.com",
            region="auto",
            access_key="AKIA-test",
            secret_key="secret-test",
        )
    return storage, client


def test_s3_storage_save_and_read():
    storage, client = _s3_with_mock_client()
    storage.save("motos/1/2.jpg", b"abc", "image/jpeg")
    client.put_object.assert_called_once_with(
        Bucket="motopay-test", Key="motos/1/2.jpg", Body=b"abc", ContentType="image/jpeg"
    )

    client.get_object.return_value = {"Body": io.BytesIO(b"abc")}
    assert storage.read("motos/1/2.jpg") == b"abc"


def test_s3_storage_read_missing_returns_none():
    from botocore.exceptions import ClientError

    storage, client = _s3_with_mock_client()
    client.get_object.side_effect = ClientError(
        {"Error": {"Code": "NoSuchKey"}}, "GetObject"
    )
    assert storage.read("motos/9/9.jpg") is None


def test_s3_storage_read_propagates_real_error():
    from botocore.exceptions import ClientError

    storage, client = _s3_with_mock_client()
    client.get_object.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied"}}, "GetObject"
    )
    with pytest.raises(ClientError):
        storage.read("motos/1/2.jpg")


def test_s3_storage_exists():
    from botocore.exceptions import ClientError

    storage, client = _s3_with_mock_client()
    client.head_object.return_value = {}
    assert storage.exists("motos/1/2.jpg") is True

    client.head_object.side_effect = ClientError(
        {"Error": {"Code": "404"}, "ResponseMetadata": {"HTTPStatusCode": 404}}, "HeadObject"
    )
    assert storage.exists("motos/1/2.jpg") is False


def test_s3_storage_requires_bucket():
    with patch("boto3.client", return_value=MagicMock()):
        with pytest.raises(RuntimeError, match="S3_BUCKET"):
            S3Storage(bucket="", endpoint_url="", region="", access_key="k", secret_key="s")
