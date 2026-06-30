from __future__ import annotations

import uuid
from pathlib import PurePosixPath

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from motopay.domain.enums import UserRole
from motopay.domain.exceptions import ForbiddenError, MotoPayError, NotFoundError
from motopay.infrastructure.db.models import Anexo
from motopay.infrastructure.storage import get_storage
from motopay.interfaces.api.deps import CurrentUser

ALLOWED_CONTENT_TYPES: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "application/pdf": ".pdf",
}
MAX_ANEXO_BYTES = 20 * 1024 * 1024

_SCOPED_ROLES = frozenset({UserRole.DONO})


def _assert_scope(user: CurrentUser, operacao_scope: int | None, anexo: Anexo) -> None:
    if user.role in _SCOPED_ROLES and anexo.operacao_id != user.operacao_id:
        raise ForbiddenError("Anexo fora do escopo")
    if (
        user.role == UserRole.ADMIN
        and operacao_scope is not None
        and anexo.operacao_id != operacao_scope
    ):
        raise ForbiddenError("Anexo fora do escopo informado")


def _storage_key(operacao_id: int, entidade_tipo: str, entidade_id: int, extension: str) -> str:
    return f"anexos/{operacao_id}/{entidade_tipo}/{entidade_id}/{uuid.uuid4().hex}{extension}"


def count_anexos(db: Session, entidade_tipo: str, entidade_id: int) -> int:
    return int(
        db.scalar(
            select(func.count(Anexo.id)).where(
                Anexo.entidade_tipo == entidade_tipo, Anexo.entidade_id == entidade_id
            )
        )
        or 0
    )


def list_anexos(
    db: Session, operacao_id: int, entidade_tipo: str, entidade_id: int
) -> list[Anexo]:
    return list(
        db.scalars(
            select(Anexo)
            .where(
                Anexo.operacao_id == operacao_id,
                Anexo.entidade_tipo == entidade_tipo,
                Anexo.entidade_id == entidade_id,
            )
            .order_by(Anexo.id.desc())
        ).all()
    )


async def upload_anexo(
    db: Session,
    *,
    operacao_id: int,
    entidade_tipo: str,
    entidade_id: int,
    upload: UploadFile,
) -> Anexo:
    content_type = (upload.content_type or "").lower()
    extension = ALLOWED_CONTENT_TYPES.get(content_type)
    if extension is None:
        raise MotoPayError("Tipo de arquivo não suportado (use PDF, JPEG, PNG ou WebP)")

    data = await upload.read()
    if not data:
        raise MotoPayError("Arquivo vazio")
    if len(data) > MAX_ANEXO_BYTES:
        raise MotoPayError("Arquivo excede o limite de 20 MB")

    key = _storage_key(operacao_id, entidade_tipo, entidade_id, extension)
    get_storage().save(key, data, content_type)

    filename = PurePosixPath(upload.filename or f"anexo{extension}").name[:255]
    anexo = Anexo(
        operacao_id=operacao_id,
        entidade_tipo=entidade_tipo,
        entidade_id=entidade_id,
        storage_key=key,
        filename=filename,
        content_type=content_type,
        tamanho=len(data),
    )
    db.add(anexo)
    db.commit()
    db.refresh(anexo)
    return anexo


def get_anexo_bytes(
    db: Session, user: CurrentUser, operacao_scope: int | None, anexo_id: int
) -> tuple[bytes, str, str]:
    anexo = db.get(Anexo, anexo_id)
    if not anexo:
        raise NotFoundError("Anexo não encontrado")
    _assert_scope(user, operacao_scope, anexo)
    data = get_storage().read(anexo.storage_key)
    if data is None:
        raise NotFoundError("Anexo não encontrado")
    return data, anexo.content_type, anexo.filename


def delete_anexo(
    db: Session, user: CurrentUser, operacao_scope: int | None, anexo_id: int
) -> None:
    anexo = db.get(Anexo, anexo_id)
    if not anexo:
        raise NotFoundError("Anexo não encontrado")
    _assert_scope(user, operacao_scope, anexo)
    key = anexo.storage_key
    db.delete(anexo)
    db.commit()
    get_storage().delete(key)


def delete_anexos_for_entity(
    db: Session,
    entidade_tipo: str,
    entidade_id: int,
    operacao_id: int,
    *,
    commit: bool = True,
) -> None:
    """Remove todos os anexos (storage + linhas) de uma entidade. Usado ao excluir a entidade.

    Filtra por ``operacao_id`` (defesa em profundidade — nunca apaga anexos de outra operação).
    Ordem: storage best-effort PRIMEIRO, depois as linhas no banco; com ``commit=False`` o
    chamador comita junto com a exclusão da entidade-pai (uma única transação, sem órfãos).
    """
    anexos = list(
        db.scalars(
            select(Anexo).where(
                Anexo.operacao_id == operacao_id,
                Anexo.entidade_tipo == entidade_tipo,
                Anexo.entidade_id == entidade_id,
            )
        ).all()
    )
    storage = get_storage()
    for anexo in anexos:
        try:
            storage.delete(anexo.storage_key)
        except Exception:  # noqa: BLE001 - limpeza best-effort do storage
            pass
    for anexo in anexos:
        db.delete(anexo)
    if commit:
        db.commit()
