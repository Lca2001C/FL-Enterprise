from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class S3Storage:
    """Storage S3-compatível (AWS S3, Cloudflare R2, Backblaze B2, Spaces, MinIO).

    Os objetos sobrevivem a redeploys/reinícios do container — recomendado em
    plataformas de disco efêmero. As imagens continuam sendo servidas pela API
    (streaming), preservando o controle de acesso por operação.
    """

    def __init__(
        self,
        *,
        bucket: str,
        endpoint_url: str,
        region: str,
        access_key: str,
        secret_key: str,
    ) -> None:
        try:
            import boto3
            from botocore.config import Config
        except ImportError as exc:  # pragma: no cover - dependência sempre presente na imagem
            raise RuntimeError(
                "STORAGE_BACKEND=s3 requer o pacote boto3 (já incluído na imagem de produção)."
            ) from exc

        if not bucket:
            raise RuntimeError("STORAGE_BACKEND=s3 exige S3_BUCKET configurado.")

        self._bucket = bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url.strip() or None,  # vazio = AWS; preencha p/ R2/B2/MinIO
            region_name=region.strip() or None,
            aws_access_key_id=access_key.strip() or None,
            aws_secret_access_key=secret_key.strip() or None,
            config=Config(signature_version="s3v4", retries={"max_attempts": 3, "mode": "standard"}),
        )
        # Importado aqui para uso nos handlers de erro (404 vs falha real).
        from botocore.exceptions import ClientError

        self._ClientError = ClientError

    def save(self, key: str, data: bytes, content_type: str) -> None:
        self._client.put_object(
            Bucket=self._bucket, Key=key, Body=data, ContentType=content_type
        )

    def read(self, key: str) -> bytes | None:
        try:
            resp = self._client.get_object(Bucket=self._bucket, Key=key)
            return resp["Body"].read()
        except self._ClientError as exc:
            if _is_not_found(exc):
                return None
            raise

    def delete(self, key: str) -> None:
        # delete_object é idempotente no S3 (não falha se a chave não existir).
        self._client.delete_object(Bucket=self._bucket, Key=key)

    def exists(self, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self._bucket, Key=key)
            return True
        except self._ClientError as exc:
            if _is_not_found(exc):
                return False
            raise


def _is_not_found(exc: object) -> bool:
    code = getattr(exc, "response", {}).get("Error", {}).get("Code", "")
    status = getattr(exc, "response", {}).get("ResponseMetadata", {}).get("HTTPStatusCode")
    return code in ("NoSuchKey", "NoSuchBucket", "404", "NotFound") or status == 404
