from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ObjectStorage(Protocol):
    """Contrato mínimo de armazenamento de objetos por chave (ex.: motos/3/12.jpg)."""

    def save(self, key: str, data: bytes, content_type: str) -> None:
        """Grava (sobrescrevendo) o objeto na chave informada."""
        ...

    def read(self, key: str) -> bytes | None:
        """Lê o objeto; retorna None se não existir."""
        ...

    def delete(self, key: str) -> None:
        """Remove o objeto; idempotente (não falha se ausente)."""
        ...

    def exists(self, key: str) -> bool:
        """Indica se o objeto existe."""
        ...
