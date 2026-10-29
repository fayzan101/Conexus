from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.models import Document, ProjectMembership, Role, User

_CLEARANCE_RANK = {
    "public": 0,
    "internal": 1,
    "confidential": 2,
    "restricted": 3,
}


@dataclass
class AccessDecision:
    allowed: bool
    reason: str = ""


def clearance_allows(user_clearance: str | None, doc_classification: str | None) -> bool:
    u = _CLEARANCE_RANK.get((user_clearance or "internal").lower(), 1)
    d = _CLEARANCE_RANK.get((doc_classification or "internal").lower(), 1)
    return u >= d


def evaluate_document_access(
    db: Session,
    *,
    user: User | None,
    user_id: UUID | None,
    tenant_id: str | None,
    document: Document | None,
    payload: dict | None = None,
    settings: Settings | None = None,
) -> AccessDecision:
    payload = payload or {}
    cfg = settings or get_settings()
    if tenant_id and document and document.tenant_id != tenant_id:
        return AccessDecision(False, "tenant_mismatch")
    if tenant_id and payload.get("tenant_id") and payload.get("tenant_id") != tenant_id:
        return AccessDecision(False, "tenant_mismatch")

    if user is None and user_id:
        user = db.get(User, user_id)
    if user is None:
        return AccessDecision(False, "unauthenticated")

    visibility = (document.visibility if document else payload.get("visibility")) or "org"
    classification = (document.classification if document else payload.get("classification")) or "internal"
    region = (document.region if document else payload.get("region")) or None
    project_id = document.project_id if document else payload.get("project_id")
    uploaded_by = document.uploaded_by if document else None
    principals = payload.get("principals") or []

    if visibility == "private":
        if uploaded_by != user.id and user.role != Role.admin:
            return AccessDecision(False, "private_owner_only")

    if not clearance_allows(user.clearance, classification):
        return AccessDecision(False, f"classification_denied:{classification}")

    if region and user.region and region.lower() != user.region.lower() and user.role != Role.admin:
        return AccessDecision(False, f"region_denied:{region}")

    if project_id and user.role != Role.admin:
        member = (
            db.query(ProjectMembership)
            .filter(
                ProjectMembership.project_id == UUID(str(project_id)),
                ProjectMembership.user_id == user.id,
            )
            .first()
        )
        any_members = (
            db.query(ProjectMembership).filter(ProjectMembership.project_id == UUID(str(project_id))).first()
        )
        if not member:
            # Default deny when project-scoped; pilot may open empty projects
            if any_members or not cfg.project_open_if_empty:
                return AccessDecision(False, "project_membership_required")

    if principals:
        principal_ok = str(user.id) in principals or user.email in principals or user.role == Role.admin
        if not principal_ok:
            return AccessDecision(False, "principal_acl_denied")

    return AccessDecision(True, "allowed")


def filter_hits_with_reasons(
    db: Session,
    hits: list[dict],
    *,
    user_id: UUID | None,
    tenant_id: str | None = None,
) -> tuple[list[dict], list[dict]]:
    """Return (allowed_hits, blocked_summaries)."""
    user = db.get(User, user_id) if user_id else None
    allowed: list[dict] = []
    blocked: list[dict] = []
    for hit in hits:
        payload = hit.get("payload") or {}
        doc = None
        doc_id = payload.get("document_id")
        if doc_id:
            try:
                doc = db.get(Document, UUID(str(doc_id)))
            except Exception:
                doc = None
        decision = evaluate_document_access(
            db,
            user=user,
            user_id=user_id,
            tenant_id=tenant_id,
            document=doc,
            payload=payload,
        )
        if decision.allowed:
            allowed.append(hit)
        else:
            from app.services.observability import record_acl_drop

            record_acl_drop(decision.reason or "unknown")
            blocked.append(
                {
                    "id": str(hit.get("id")),
                    "title": payload.get("title"),
                    "reason": decision.reason,
                }
            )
    return allowed, blocked
