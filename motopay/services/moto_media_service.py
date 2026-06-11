from __future__ import annotations

from pathlib import PurePosixPath

from fastapi import UploadFile
from sqlalchemy.orm import Session

from motopay.domain.exceptions import MotoPayError, NotFoundError
from motopay.infrastructure.db.models import Moto
from motopay.infrastructure.storage import get_storage
from motopay.interfaces.api.deps import CurrentUser
from motopay.services.fleet_service import get_moto

ALLOWED_CONTENT_TYPES: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
MAX_IMAGE_BYTES = 15 * 1024 * 1024


def _storage_key(moto: Moto, extension: str) -> str:
    # Chave estável por operação/moto — funciona igual em disco e em S3.
    return f"motos/{moto.operacao_id}/{moto.id}{extension}"


def _media_type_for(key: str) -> str:
    suffix = PurePosixPath(key).suffix.lower()
    return next(
        (ct for ct, ext in ALLOWED_CONTENT_TYPES.items() if ext == suffix),
        "application/octet-stream",
    )


async def save_moto_imagem(
    db: Session,
    user: CurrentUser,
    operacao_scope: int | None,
    moto_id: int,
    upload: UploadFile,
) -> Moto:
    moto = get_moto(db, user, operacao_scope, moto_id)
    content_type = (upload.content_type or "").lower()
    extension = ALLOWED_CONTENT_TYPES.get(content_type)
    if extension is None:
        raise MotoPayError("Tipo de imagem não suportado (use JPEG, PNG ou WebP)")

    data = await upload.read()
    if not data:
        raise MotoPayError("Arquivo de imagem vazio")
    if len(data) > MAX_IMAGE_BYTES:
        raise MotoPayError("Imagem excede o limite de 15 MB")

    storage = get_storage()
    key = _storage_key(moto, extension)
    old_key = moto.imagem_path

    storage.save(key, data, content_type)

    moto.imagem_path = key
    db.add(moto)
    db.commit()
    db.refresh(moto)

    # Remove a imagem antiga só se a chave mudou (ex.: jpg → png).
    if old_key and old_key != key:
        storage.delete(old_key)

    return moto


def get_moto_imagem_bytes(
    db: Session,
    user: CurrentUser,
    operacao_scope: int | None,
    moto_id: int,
) -> tuple[bytes, str]:
    moto = get_moto(db, user, operacao_scope, moto_id)
    if not moto.imagem_path:
        raise NotFoundError("Imagem não encontrada")
    data = get_storage().read(moto.imagem_path)
    if data is None:
        raise NotFoundError("Imagem não encontrada")
    return data, _media_type_for(moto.imagem_path)


def delete_moto_imagem(
    db: Session,
    user: CurrentUser,
    operacao_scope: int | None,
    moto_id: int,
) -> Moto:
    moto = get_moto(db, user, operacao_scope, moto_id)
    if not moto.imagem_path:
        raise NotFoundError("Imagem não encontrada")
    old_key = moto.imagem_path
    moto.imagem_path = None
    db.add(moto)
    db.commit()
    db.refresh(moto)
    get_storage().delete(old_key)
    return moto
