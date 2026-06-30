from __future__ import annotations

import logging

from cryptography.fernet import Fernet, InvalidToken

from motopay.config import get_settings

_logger = logging.getLogger(__name__)

_FERNET_PREFIX = "gAAAA"


def _fernet() -> Fernet | None:
    key = get_settings().encryption_key.strip()
    if not key:
        return None
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except (ValueError, TypeError):
        _logger.error("ENCRYPTION_KEY inválida — use Fernet.generate_key()")
        return None


def _looks_encrypted(value: str) -> bool:
    return value.startswith(_FERNET_PREFIX)


def encrypt_token(plain: str | None) -> str | None:
    if plain is None:
        return None
    value = plain.strip()
    if not value:
        return None
    if _looks_encrypted(value):
        return value
    f = _fernet()
    if f is None:
        return value
    return f.encrypt(value.encode()).decode()


def decrypt_token(cipher: str | None, *, operacao_id: int | None = None) -> str:
    if not cipher:
        return ""
    value = cipher.strip()
    if not value:
        return ""
    if not _looks_encrypted(value):
        return value
    f = _fernet()
    if f is None:
        return value
    try:
        return f.decrypt(value.encode()).decode()
    except InvalidToken:
        _logger.warning(
            "mp_token_decrypt_failed operacao_id=%s — chave de encriptação incorreta ou dado corrompido",
            operacao_id,
        )
        return ""


def generate_encryption_key() -> str:
    return Fernet.generate_key().decode()
