from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from motopay.domain.exceptions import UnauthorizedError
from motopay.infrastructure.db.session import get_db
from motopay.interfaces.api.deps import CurrentUser, get_current_user
from motopay.interfaces.api.schemas import LoginRequest, TokenResponse, UserOut
from motopay.services.auth_service import authenticate_user, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        user = authenticate_user(db, body.email, body.password)
    except UnauthorizedError:
        raise HTTPException(status_code=401, detail="Credenciais inválidas") from None
    token = create_access_token(user=user)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserOut)
def read_me(user: CurrentUser = Depends(get_current_user)) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        tipo=user.role,
        operacao_id=user.operacao_id,
    )
