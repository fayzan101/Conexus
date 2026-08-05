from __future__ import annotations

import hashlib
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any
from uuid import UUID

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.models import InviteToken, Role, User
from app.db.session import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)

_jwks_cache: dict[str, Any] = {"fetched_at": 0.0, "keys": {}}


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str | None) -> bool:
    if not hashed:
        return False
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str, role: str, settings: Settings) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": subject, "role": role, "type": "access", "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def create_refresh_token(subject: str, settings: Settings) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    payload = {"sub": subject, "type": "refresh", "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if not user or not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def _fetch_jwks(settings: Settings) -> dict[str, Any]:
    now = time.time()
    if _jwks_cache["keys"] and now - float(_jwks_cache["fetched_at"]) < 3600:
        return _jwks_cache["keys"]

    jwks_url = settings.auth_jwks_url
    if not jwks_url and settings.auth_issuer:
        jwks_url = settings.auth_issuer.rstrip("/") + "/.well-known/jwks.json"
    if not jwks_url:
        raise HTTPException(status_code=500, detail="AUTH_JWKS_URL or AUTH_ISSUER required for OIDC")

    with httpx.Client(timeout=15.0) as client:
        resp = client.get(jwks_url)
        resp.raise_for_status()
        data = resp.json()
    keys = {k["kid"]: k for k in data.get("keys", []) if k.get("kid")}
    _jwks_cache["keys"] = keys
    _jwks_cache["fetched_at"] = now
    return keys


def decode_oidc_token(token: str, settings: Settings) -> dict[str, Any]:
    try:
        header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid token header") from exc
    kid = header.get("kid")
    keys = _fetch_jwks(settings)
    key = keys.get(kid) if kid else None
    if not key and len(keys) == 1:
        key = next(iter(keys.values()))
    if not key:
        raise HTTPException(status_code=401, detail="Unknown signing key")

    options = {"verify_aud": bool(settings.auth_audience)}
    try:
        return jwt.decode(
            token,
            key,
            algorithms=[header.get("alg") or "RS256"],
            audience=settings.auth_audience or None,
            issuer=settings.auth_issuer or None,
            options=options,
        )
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid OIDC token") from exc


def upsert_oidc_user(db: Session, claims: dict[str, Any]) -> User:
    sub = claims.get("sub")
    email = (claims.get("email") or claims.get("preferred_username") or "").lower()
    if not sub or not email:
        raise HTTPException(status_code=401, detail="OIDC token missing sub/email")

    user = db.query(User).filter(User.idp_subject == sub).first()
    if not user:
        user = get_user_by_email(db, email)
    if not user:
        user = User(
            email=email,
            full_name=claims.get("name") or email.split("@")[0],
            idp_subject=sub,
            hashed_password=None,
            role=Role.employee,
            is_active=True,
        )
        db.add(user)
    else:
        user.idp_subject = sub
        if claims.get("name"):
            user.full_name = claims.get("name")
    db.commit()
    db.refresh(user)
    return user


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    token = credentials.credentials

    if settings.auth_provider == "oidc":
        # Prefer IdP JWT; fall back to local session tokens issued after OIDC exchange
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
            if payload.get("type") not in {None, "access"}:
                raise HTTPException(status_code=401, detail="Invalid token type")
            sub = payload.get("sub")
            if not sub:
                raise HTTPException(status_code=401, detail="Invalid token")
            user = db.get(User, UUID(sub))
            if not user or not user.is_active:
                raise HTTPException(status_code=401, detail="User inactive or missing")
            return user
        except (JWTError, ValueError, HTTPException):
            claims = decode_oidc_token(token, settings)
            user = upsert_oidc_user(db, claims)
            if not user.is_active:
                raise HTTPException(status_code=401, detail="User inactive")
            return user

    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        if payload.get("type") not in {None, "access"}:
            raise HTTPException(status_code=401, detail="Invalid token type")
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        user_id = UUID(sub)
    except (JWTError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive or missing")
    return user


def require_roles(*roles: Role):
    def _checker(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in roles and user.role != Role.admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return _checker


def hash_invite_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def create_invite(
    db: Session,
    *,
    email: str,
    role: Role,
    invited_by: UUID | None,
    settings: Settings,
) -> tuple[InviteToken, str]:
    raw = secrets.token_urlsafe(32)
    invite = InviteToken(
        email=email.lower(),
        role=role,
        token_hash=hash_invite_token(raw),
        invited_by=invited_by,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=settings.auth_invite_expire_hours),
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)
    return invite, raw


def accept_invite(db: Session, *, raw_token: str, password: str, full_name: str | None) -> User:
    token_hash = hash_invite_token(raw_token)
    invite = db.query(InviteToken).filter(InviteToken.token_hash == token_hash).first()
    if not invite or invite.accepted_at:
        raise HTTPException(status_code=400, detail="Invalid invite")
    expires = invite.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invite expired")

    user = get_user_by_email(db, invite.email)
    if not user:
        user = User(
            email=invite.email,
            full_name=full_name or invite.email.split("@")[0],
            hashed_password=hash_password(password),
            role=invite.role,
            is_active=True,
        )
        db.add(user)
    else:
        user.hashed_password = hash_password(password)
        user.role = invite.role
        if full_name:
            user.full_name = full_name
        user.is_active = True

    invite.accepted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    return user


def clear_jwks_cache() -> None:
    _jwks_cache["keys"] = {}
    _jwks_cache["fetched_at"] = 0.0


CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]
