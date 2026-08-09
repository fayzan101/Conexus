from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError, jwt

from app.db.models import Role, User
from app.deps import (
    AppSettings,
    CurrentUser,
    DbSession,
    accept_invite,
    authenticate_user,
    create_access_token,
    create_invite,
    create_refresh_token,
    decode_oidc_token,
    require_roles,
    upsert_oidc_user,
)
from app.schemas import (
    InviteAcceptRequest,
    InviteCreateRequest,
    InviteCreateResponse,
    LoginRequest,
    OidcExchangeRequest,
    RefreshRequest,
    TokenResponse,
    UserOut,
)

router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: DbSession, settings: AppSettings):
    if settings.auth_provider != "dev":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Password login disabled for AUTH_PROVIDER={settings.auth_provider}. "
                "Use POST /v1/auth/oidc/exchange with an IdP token."
            ),
        )
    user = authenticate_user(db, payload.email, payload.password, tenant_id=settings.default_tenant_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    access = create_access_token(str(user.id), user.role.value, settings)
    refresh = create_refresh_token(str(user.id), settings)
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/oidc/exchange", response_model=TokenResponse)
def oidc_exchange(payload: OidcExchangeRequest, db: DbSession, settings: AppSettings):
    """Exchange a validated IdP access/ID token for an Enterprise Brain session."""
    if settings.auth_provider != "oidc":
        raise HTTPException(status_code=400, detail="Set AUTH_PROVIDER=oidc to use OIDC exchange")
    id_token = payload.id_token or payload.access_token
    if not id_token:
        raise HTTPException(status_code=400, detail="id_token or access_token required")
    claims = decode_oidc_token(id_token, settings)
    user = upsert_oidc_user(db, claims)
    access = create_access_token(str(user.id), user.role.value, settings)
    refresh = create_refresh_token(str(user.id), settings)
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: DbSession, settings: AppSettings):
    try:
        data = jwt.decode(payload.refresh_token, settings.secret_key, algorithms=["HS256"])
        if data.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        user = db.get(User, UUID(data["sub"]))
    except (JWTError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=401, detail="Invalid refresh token") from exc
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User inactive or missing")
    access = create_access_token(str(user.id), user.role.value, settings)
    new_refresh = create_refresh_token(str(user.id), settings)
    return TokenResponse(access_token=access, refresh_token=new_refresh)


@router.post("/invites", response_model=InviteCreateResponse)
def create_user_invite(
    payload: InviteCreateRequest,
    db: DbSession,
    settings: AppSettings,
    user: Annotated[User, Depends(require_roles(Role.admin))],
):
    invite, raw = create_invite(
        db,
        email=payload.email,
        role=payload.role,
        invited_by=user.id,
        settings=settings,
    )
    accept_url = f"{settings.app_base_url}/invite?token={raw}"
    return InviteCreateResponse(invite_id=invite.id, email=invite.email, accept_url=accept_url, token=raw)


@router.post("/invites/accept", response_model=TokenResponse)
def accept_user_invite(payload: InviteAcceptRequest, db: DbSession, settings: AppSettings):
    user = accept_invite(db, raw_token=payload.token, password=payload.password, full_name=payload.full_name)
    access = create_access_token(str(user.id), user.role.value, settings)
    refresh_tok = create_refresh_token(str(user.id), settings)
    return TokenResponse(access_token=access, refresh_token=refresh_tok)


@router.post("/logout")
def logout(_: CurrentUser):
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return user
