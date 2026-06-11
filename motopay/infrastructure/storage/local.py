from __future__ import annotations

from pathlib import Path

from motopay.domain.exceptions import MotoPayError


class LocalStorage:
    """Storage em disco local (UPLOAD_DIR).

    Persistente apenas se o diretório estiver em um volume durável (volume Docker
    nomeado ou disco persistente). Em plataformas de disco efêmero, use S3.
    """

    def __init__(self, root: Path) -> None:
        self._root = Path(root).resolve()

    def _abs(self, key: str) -> Path:
        target = (self._root / key).resolve()
        # Defesa contra path traversal (a chave é montada internamente, mas garante).
        if not str(target).startswith(str(self._root)):
            raise MotoPayError("Caminho de imagem inválido")
        return target

    def save(self, key: str, data: bytes, content_type: str) -> None:
        del content_type  # irrelevante para disco; o tipo é derivado da extensão na leitura
        path = self._abs(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def read(self, key: str) -> bytes | None:
        path = self._abs(key)
        return path.read_bytes() if path.is_file() else None

    def delete(self, key: str) -> None:
        path = self._abs(key)
        if path.is_file():
            path.unlink()

    def exists(self, key: str) -> bool:
        return self._abs(key).is_file()
