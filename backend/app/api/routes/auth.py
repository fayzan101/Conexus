from fastapi import APIRouter, HTTPException, status

from app.deps import AppSettings, CurrentUser, DbSession, authenticate_user, create_access_token
from app.schemas import LoginRequest, TokenResponse, UserOut

router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: DbSession, settings: AppSettings):
    if settings.auth_provider != "dev":
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"Auth provider '{settings.auth_provider}' not wired yet; use AUTH_PROVIDER=dev",
        )
    user = authenticate_user(db, payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token(str(user.id), user.role.value, settings)
    return TokenResponse(access_token=token)


@router.post("/logout")
def logout(_: CurrentUser):
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return user
