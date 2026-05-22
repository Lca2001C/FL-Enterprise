from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from motopay.domain.exceptions import UnauthorizedError
from motopay.infrastructure.db.models import Usuario
from motopay.infrastructure.db.session import get_db
from motopay.infrastructure.security.client_ip import get_client_ip
from motopay.infrastructure.security.rate_limit import (
    assert_login_not_blocked,
    assert_refresh_not_blocked,
    clear_login_attempts,
    clear_refresh_attempts,
    record_login_failure,
    record_refresh_failure,
)
from motopay.infrastructure.security.refresh_tokens import (
    create_refresh_token,
    revoke_all_refresh_tokens_for_user,
    revoke_refresh_token,
    validate_refresh_token,
)
from motopay.interfaces.api.deps import CurrentUser, get_current_user
from motopay.interfaces.api.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    UserOut,
)
from motopay.services.auth_service import authenticate_user, change_password, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


def _issue_tokens(*, user: Usuario) -> TokenResponse:
    access = create_access_token(user=user)
    refresh = create_refresh_token(user.id)
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    ip = get_client_ip(request)
    assert_login_not_blocked(ip, body.email)
    try:
        user = authenticate_user(db, body.email, body.password)
    except UnauthorizedError:
        record_login_failure(ip, body.email)
        raise HTTPException(status_code=401, detail="Credenciais inválidas") from None
    clear_login_attempts(ip, body.email)
    return _issue_tokens(user=user)


@router.post("/refresh", response_model=TokenResponse)
def refresh_tokens(
    body: RefreshRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    ip = get_client_ip(request)
    assert_refresh_not_blocked(ip)
    user_id = validate_refresh_token(body.refresh_token)
    if user_id is None:
        record_refresh_failure(ip)
        raise HTTPException(status_code=401, detail="Refresh token inválido ou expirado")
    user = db.get(Usuario, user_id)
    if not user:
        revoke_refresh_token(body.refresh_token)
        record_refresh_failure(ip)
        raise HTTPException(status_code=401, detail="Refresh token inválido ou expirado")
    revoke_refresh_token(body.refresh_token)
    clear_refresh_attempts(ip)
    return _issue_tokens(user=user)


@router.post("/logout")
def logout(body: RefreshRequest) -> dict[str, bool]:
    if validate_refresh_token(body.refresh_token) is not None:
        revoke_refresh_token(body.refresh_token)
    return {"ok": True}


@router.post("/logout-all")
def logout_all(
    user: CurrentUser = Depends(get_current_user),
) -> dict[str, int]:
    removed = revoke_all_refresh_tokens_for_user(user.id)
    return {"ok": True, "revoked": removed}


@router.post("/change-password")
def change_password_route(
    body: ChangePasswordRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    try:
        change_password(db, user.id, current=body.current_password, new=body.new_password)
    except UnauthorizedError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    revoke_all_refresh_tokens_for_user(user.id)
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def read_me(user: CurrentUser = Depends(get_current_user)) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        tipo=user.role,
        operacao_id=user.operacao_id,
    )
