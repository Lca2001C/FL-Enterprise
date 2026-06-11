"""Armazenamento de objetos (imagens de motos) com backend plugável.

- `local` (padrão): disco em UPLOAD_DIR — ideal para dev e para VPS com volume
  Docker persistente (docker-compose.prod.yml monta `uploads_data`).
- `s3`: qualquer storage S3-compatível (AWS S3, Cloudflare R2, Backblaze B2,
  DigitalOcean Spaces, MinIO, Supabase Storage) — obrigatório em plataformas
  com disco efêmero (Render, Railway), onde arquivos somem no redeploy.

Selecionado por STORAGE_BACKEND no .env. Veja DEPLOY.md.
"""

from __future__ import annotations

from pathlib import Path

from motopay.config import get_settings
from motopay.infrastructure.storage.base import ObjectStorage
from motopay.infrastructure.storage.local import LocalStorage

__all__ = ["ObjectStorage", "get_storage"]


def get_storage() -> ObjectStorage:
    """Retorna o backend de storage configurado.

    Não cacheado de propósito: lê as settings atuais a cada chamada (uploads de
    imagem são pouco frequentes) para que mudanças de UPLOAD_DIR em testes/runtime
    sejam respeitadas sem invalidação de cache.
    """
    settings = get_settings()
    backend = (settings.storage_backend or "local").strip().lower()
    if backend == "s3":
        from motopay.infrastructure.storage.s3 import S3Storage

        return S3Storage(
            bucket=settings.s3_bucket,
            endpoint_url=settings.s3_endpoint_url,
            region=settings.s3_region,
            access_key=settings.s3_access_key_id,
            secret_key=settings.s3_secret_access_key,
        )
    return LocalStorage(Path(settings.upload_dir))
