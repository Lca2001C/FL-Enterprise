from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from motopay.domain.enums import UserRole
from motopay.domain.exceptions import ForbiddenError, UnauthorizedError
from motopay.services.auth_service import decode_token

security = HTTPBearer(auto_error=False)

_OPERACIONAL_ROLES = frozenset({UserRole.ADMIN, UserRole.DONO, UserRole.OPERADOR})


@dataclass
class CurrentUser:
    id: int
    email: str
    role: UserRole
    operacao_id: int | None
    cliente_id: int | None = None


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> CurrentUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError("Autenticação necessária")
    data = decode_token(credentials.credentials)
    try:
        user_id = int(data["sub"])
        email = str(data["email"])
        role = UserRole(data["role"])
        operacao_id = data.get("operacao_id")
        if operacao_id is not None:
            operacao_id = int(operacao_id)
        cliente_id = data.get("cliente_id")
        if cliente_id is not None:
            cliente_id = int(cliente_id)
    except (KeyError, ValueError, TypeError) as e:
        raise UnauthorizedError("Token malformado") from e
    return CurrentUser(
        id=user_id,
        email=email,
        role=role,
        operacao_id=operacao_id,
        cliente_id=cliente_id,
    )


def require_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if user.role != UserRole.ADMIN:
        raise ForbiddenError("Acesso restrito a administradores")
    return user


def require_dono_or_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if user.role not in (UserRole.ADMIN, UserRole.DONO):
        raise ForbiddenError("Perfil inválido")
    if user.role == UserRole.DONO and user.operacao_id is None:
        raise ForbiddenError("Operação não definida para este usuário")
    return user


def require_operacional(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if user.role not in _OPERACIONAL_ROLES:
        raise ForbiddenError("Perfil inválido")
    if user.role in (UserRole.DONO, UserRole.OPERADOR) and user.operacao_id is None:
        raise ForbiddenError("Operação não definida para este usuário")
    return user


def require_settings_access(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Dono e admin — ajustes da operação; operador não."""
    if user.role not in (UserRole.ADMIN, UserRole.DONO):
        raise ForbiddenError("Acesso restrito a dono ou administrador")
    if user.role == UserRole.DONO and user.operacao_id is None:
        raise ForbiddenError("Operação não definida para este usuário")
    return user


def require_cliente(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if user.role != UserRole.CLIENTE:
        raise ForbiddenError("Acesso restrito a clientes")
    if user.cliente_id is None:
        raise ForbiddenError("Cliente não vinculado ao usuário")
    return user


def resolve_operacao_id(
    user: CurrentUser = Depends(require_operacional),
    operacao_id: int | None = Query(
        default=None,
        description="Admin: filtra por operação. Dono/operador: ignorado (usa a operação do token).",
    ),
    x_operacao_id: int | None = Header(default=None, alias="X-Operacao-Id"),
) -> int | None:
    requested = operacao_id if operacao_id is not None else x_operacao_id
    if user.role in (UserRole.DONO, UserRole.OPERADOR):
        return user.operacao_id
    if user.role == UserRole.ADMIN:
        return requested
    return None


def operacao_scope(
    user: CurrentUser = Depends(require_operacional),
    operacao_id: int | None = Query(
        default=None,
        description="Admin: filtra por operação. Dono/operador: ignorado (usa a operação do token).",
    ),
    x_operacao_id: int | None = Header(default=None, alias="X-Operacao-Id"),
) -> tuple[CurrentUser, int | None]:
    requested = operacao_id if operacao_id is not None else x_operacao_id
    if user.role in (UserRole.DONO, UserRole.OPERADOR):
        return user, user.operacao_id
    if user.role == UserRole.ADMIN:
        return user, requested
    return user, None


OperacaoScoped = Annotated[tuple[CurrentUser, int | None], Depends(operacao_scope)]


def assert_resource_operacao(
    resource_operacao_id: int, scope_operacao_id: int | None, user: CurrentUser
) -> None:
    if user.role == UserRole.ADMIN and scope_operacao_id is None:
        return
    if scope_operacao_id is None:
        raise ForbiddenError("Informe operacao_id (query ou header) ou restrinja o escopo")
    if resource_operacao_id != scope_operacao_id:
        raise ForbiddenError("Recurso fora do escopo da operação")
