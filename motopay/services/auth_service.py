from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from motopay.config import get_settings
from motopay.domain.enums import UserRole
from motopay.domain.exceptions import UnauthorizedError
from motopay.infrastructure.db.models import Usuario

# bcrypt para novos hashes; pbkdf2_sha256 mantido para hashes legados do seed/migração.
pwd_context = CryptContext(schemes=["bcrypt", "pbkdf2_sha256"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def authenticate_user(db: Session, email: str, password: str) -> Usuario:
    user = db.scalars(select(Usuario).where(Usuario.email == email)).first()
    if not user or not verify_password(password, user.senha_hash):
        raise UnauthorizedError("Credenciais inválidas")
    if user.tipo == UserRole.DONO.value and user.operacao_id is None:
        raise UnauthorizedError("Usuário dono sem operação associada")
    return user


def create_access_token(*, user: Usuario) -> str:
    settings = get_settings()
    expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes)
    payload: dict[str, Any] = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.tipo,
        "operacao_id": user.operacao_id,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as e:
        raise UnauthorizedError("Token inválido") from e
