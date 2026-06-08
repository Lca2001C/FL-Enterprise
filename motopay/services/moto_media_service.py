from __future__ import annotations

from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from motopay.config import get_settings
from motopay.domain.exceptions import MotoPayError, NotFoundError
from motopay.infrastructure.db.models import Moto
from motopay.interfaces.api.deps import CurrentUser
from motopay.services.fleet_service import get_moto

ALLOWED_CONTENT_TYPES: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
MAX_IMAGE_BYTES = 15 * 1024 * 1024


def _upload_root() -> Path:
    return Path(get_settings().upload_dir).resolve()


def _relative_path(moto: Moto, extension: str) -> str:
    return f"motos/{moto.operacao_id}/{moto.id}{extension}"


def _absolute_path(relative: str) -> Path:
    root = _upload_root()
    target = (root / relative).resolve()
    if not str(target).startswith(str(root)):
        raise MotoPayError("Caminho de imagem inválido")
    return target


def _remove_file(relative: str | None) -> None:
    if not relative:
        return
    path = _absolute_path(relative)
    if path.is_file():
        path.unlink()


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

    relative = _relative_path(moto, extension)
    target = _absolute_path(relative)
    target.parent.mkdir(parents=True, exist_ok=True)

    old_path = moto.imagem_path
    target.write_bytes(data)

    moto.imagem_path = relative
    db.add(moto)
    db.commit()
    db.refresh(moto)

    if old_path and old_path != relative:
        _remove_file(old_path)

    return moto


def get_moto_imagem_file(
    db: Session,
    user: CurrentUser,
    operacao_scope: int | None,
    moto_id: int,
) -> tuple[Path, str]:
    moto = get_moto(db, user, operacao_scope, moto_id)
    if not moto.imagem_path:
        raise NotFoundError("Imagem não encontrada")
    path = _absolute_path(moto.imagem_path)
    if not path.is_file():
        raise NotFoundError("Imagem não encontrada")
    suffix = path.suffix.lower()
    media_type = next(
        (ct for ct, ext in ALLOWED_CONTENT_TYPES.items() if ext == suffix),
        "application/octet-stream",
    )
    return path, media_type


def delete_moto_imagem(
    db: Session,
    user: CurrentUser,
    operacao_scope: int | None,
    moto_id: int,
) -> Moto:
    moto = get_moto(db, user, operacao_scope, moto_id)
    if not moto.imagem_path:
        raise NotFoundError("Imagem não encontrada")
    old_path = moto.imagem_path
    moto.imagem_path = None
    db.add(moto)
    db.commit()
    db.refresh(moto)
    _remove_file(old_path)
    return moto
