from __future__ import annotations

import secrets
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, Field

from app.db.models import LegalHold, ProjectMembership, RetentionPolicy, Role, User
from app.deps import AppSettings, CurrentUser, DbSession, hash_password, require_roles
from app.services.audit import export_audit_logs, write_audit
from app.services.saml_auth import exchange_saml_for_session, saml_login_redirect, saml_metadata_xml
from app.services.security import (
    dsr_delete_user_data,
    ensure_tenant_key,
    rotate_connector_tokens,
    rotate_tenant_key,
    run_retention_job,
    security_posture,
)
from app.schemas import TokenResponse

router = APIRouter(tags=["security"])


def _require_scim(settings: AppSettings, authorization: str | None) -> None:
    if not settings.scim_bearer_token:
        raise HTTPException(status_code=503, detail="SCIM_BEARER_TOKEN not configured")
    if not authorization or authorization != f"Bearer {settings.scim_bearer_token}":
        raise HTTPException(status_code=401, detail="Invalid SCIM bearer token")


class ScimUser(BaseModel):
    userName: EmailStr
    active: bool = True
    displayName: str | None = None
    externalId: str | None = None
    region: str | None = None
    clearance: str | None = "internal"
    roles: list[str] | None = None


@router.get("/v1/auth/saml/metadata")
def saml_metadata(settings: AppSettings):
    return Response(content=saml_metadata_xml(settings), media_type="application/xml")


@router.get("/v1/auth/saml/login")
def saml_login(settings: AppSettings):
    if settings.auth_provider not in {"saml", "oidc"}:
        # Allow login URL generation when explicitly configured
        pass
    try:
        url = saml_login_redirect(settings)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"redirect_url": url}


@router.post("/v1/auth/saml/acs", response_model=TokenResponse)
async def saml_acs(request: Request, db: DbSession, settings: AppSettings):
    form = await request.form()
    saml_response = form.get("SAMLResponse")
    if not saml_response:
        raise HTTPException(status_code=400, detail="SAMLResponse required")
    try:
        tokens = exchange_saml_for_session(db, settings, saml_response=str(saml_response))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    write_audit(
        db,
        tenant_id=settings.default_tenant_id,
        action="auth.saml_login",
        resource_type="session",
        detail={},
    )
    return TokenResponse(access_token=tokens["access_token"], refresh_token=tokens["refresh_token"])


@router.get("/scim/v2/Users")
def scim_list_users(
    db: DbSession,
    settings: AppSettings,
    authorization: Annotated[str | None, Header()] = None,
    startIndex: int = 1,
    count: int = 100,
):
    _require_scim(settings, authorization)
    users = db.query(User).filter(User.tenant_id == settings.default_tenant_id).offset(max(0, startIndex - 1)).limit(count).all()
    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": len(users),
        "Resources": [
            {
                "id": str(u.id),
                "userName": u.email,
                "displayName": u.full_name,
                "active": u.is_active,
                "externalId": u.scim_external_id,
            }
            for u in users
        ],
    }


@router.post("/scim/v2/Users", status_code=status.HTTP_201_CREATED)
def scim_create_user(
    payload: ScimUser,
    db: DbSession,
    settings: AppSettings,
    authorization: Annotated[str | None, Header()] = None,
):
    _require_scim(settings, authorization)
    existing = db.query(User).filter(User.tenant_id == settings.default_tenant_id, User.email == payload.userName.lower()).first()
    if existing:
        raise HTTPException(status_code=409, detail="User exists")
    role = Role.employee
    if payload.roles:
        try:
            role = Role(payload.roles[0])
        except Exception:
            role = Role.employee
    user = User(
        email=payload.userName.lower(),
        full_name=payload.displayName or payload.userName.split("@")[0],
        hashed_password=hash_password(secrets.token_urlsafe(16)),
        role=role,
        is_active=payload.active,
        tenant_id=settings.default_tenant_id,
        scim_external_id=payload.externalId or str(uuid4()),
        region=payload.region,
        clearance=payload.clearance or "internal",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    write_audit(
        db,
        tenant_id=user.tenant_id,
        action="scim.user_create",
        resource_type="user",
        resource_id=str(user.id),
        actor_email="scim",
    )
    return {"id": str(user.id), "userName": user.email, "active": user.is_active}


@router.patch("/scim/v2/Users/{user_id}")
def scim_patch_user(
    user_id: UUID,
    payload: dict,
    db: DbSession,
    settings: AppSettings,
    authorization: Annotated[str | None, Header()] = None,
):
    _require_scim(settings, authorization)
    user = db.get(User, user_id)
    if not user or user.tenant_id != settings.default_tenant_id:
        raise HTTPException(status_code=404, detail="User not found")
    if "active" in payload:
        user.is_active = bool(payload["active"])
    if "displayName" in payload:
        user.full_name = payload["displayName"]
    if "region" in payload:
        user.region = payload["region"]
    if "clearance" in payload:
        user.clearance = payload["clearance"]
    db.commit()
    write_audit(
        db,
        tenant_id=user.tenant_id,
        action="scim.user_patch",
        resource_type="user",
        resource_id=str(user.id),
        actor_email="scim",
        detail=payload,
    )
    return {"id": str(user.id), "active": user.is_active}


@router.delete("/scim/v2/Users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def scim_deactivate_user(
    user_id: UUID,
    db: DbSession,
    settings: AppSettings,
    authorization: Annotated[str | None, Header()] = None,
):
    _require_scim(settings, authorization)
    user = db.get(User, user_id)
    if not user or user.tenant_id != settings.default_tenant_id:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    db.commit()
    write_audit(
        db,
        tenant_id=user.tenant_id,
        action="scim.user_deactivate",
        resource_type="user",
        resource_id=str(user.id),
        actor_email="scim",
    )
    return Response(status_code=204)


class MembershipIn(BaseModel):
    user_id: UUID
    role: str = "member"


class LegalHoldIn(BaseModel):
    name: str
    reason: str | None = None


class RetentionIn(BaseModel):
    resource_type: str = "document"
    retain_days: int = Field(ge=1, le=3650)


@router.get("/v1/security/posture")
def posture(settings: AppSettings, _: CurrentUser):
    return security_posture(settings)


@router.get("/v1/security/audit/export")
def audit_export(db: DbSession, user: Annotated[User, Depends(require_roles(Role.admin, Role.auditor))]):
    return {"logs": export_audit_logs(db, tenant_id=user.tenant_id)}


@router.post("/v1/security/retention/run")
def retention_run(
    db: DbSession,
    settings: AppSettings,
    user: Annotated[User, Depends(require_roles(Role.admin))],
):
    return run_retention_job(db, settings, tenant_id=user.tenant_id)


@router.post("/v1/security/retention/policies")
def set_retention(
    payload: RetentionIn,
    db: DbSession,
    user: Annotated[User, Depends(require_roles(Role.admin))],
):
    row = (
        db.query(RetentionPolicy)
        .filter(RetentionPolicy.tenant_id == user.tenant_id, RetentionPolicy.resource_type == payload.resource_type)
        .first()
    )
    if row:
        row.retain_days = payload.retain_days
    else:
        row = RetentionPolicy(
            tenant_id=user.tenant_id,
            resource_type=payload.resource_type,
            retain_days=payload.retain_days,
        )
        db.add(row)
    db.commit()
    return {"tenant_id": user.tenant_id, "resource_type": row.resource_type, "retain_days": row.retain_days}


@router.post("/v1/security/legal-holds")
def create_hold(
    payload: LegalHoldIn,
    db: DbSession,
    user: Annotated[User, Depends(require_roles(Role.admin, Role.auditor))],
):
    hold = LegalHold(tenant_id=user.tenant_id, name=payload.name, reason=payload.reason, created_by=user.id)
    db.add(hold)
    db.commit()
    db.refresh(hold)
    write_audit(
        db,
        tenant_id=user.tenant_id,
        action="legal_hold.create",
        resource_type="legal_hold",
        resource_id=str(hold.id),
        actor_id=user.id,
        actor_email=user.email,
    )
    return {"id": str(hold.id), "name": hold.name, "active": hold.active}


@router.post("/v1/security/dsr/users/{user_id}/delete")
def dsr_delete(
    user_id: UUID,
    db: DbSession,
    settings: AppSettings,
    user: Annotated[User, Depends(require_roles(Role.admin))],
):
    from app.config import get_settings
    from app.services.graph import GraphStore
    from app.services.storage import ObjectStorage
    from app.services.vector import VectorStore

    vs = None
    graph = None
    storage = None
    try:
        vs = VectorStore(settings)
    except Exception:
        vs = None
    try:
        graph = GraphStore(settings)
    except Exception:
        graph = None
    try:
        storage = ObjectStorage(settings)
    except Exception:
        storage = None
    try:
        return dsr_delete_user_data(
            db,
            settings,
            tenant_id=user.tenant_id,
            user_id=user_id,
            vector_store=vs,
            graph=graph,
            object_storage=storage,
        )
    finally:
        if graph:
            try:
                graph.close()
            except Exception:
                pass


@router.post("/v1/security/secrets/rotate")
def rotate_secrets(
    db: DbSession,
    settings: AppSettings,
    user: Annotated[User, Depends(require_roles(Role.admin, Role.ai_administrator))],
):
    ensure_tenant_key(db, settings, user.tenant_id)
    key = rotate_tenant_key(db, settings, user.tenant_id)
    connectors = rotate_connector_tokens(db, settings, tenant_id=user.tenant_id)
    return {"key_rotated_at": key.rotated_at.isoformat() if key.rotated_at else None, **connectors}


@router.post("/v1/projects/{project_id}/members")
def add_member(
    project_id: UUID,
    payload: MembershipIn,
    db: DbSession,
    user: Annotated[User, Depends(require_roles(Role.admin, Role.manager))],
):
    row = ProjectMembership(
        tenant_id=user.tenant_id,
        project_id=project_id,
        user_id=payload.user_id,
        role=payload.role,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": str(row.id), "project_id": str(project_id), "user_id": str(payload.user_id)}
