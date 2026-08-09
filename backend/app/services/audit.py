from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import AuditLog


def write_audit(
    db: Session,
    *,
    tenant_id: str,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    actor_id: UUID | None = None,
    actor_email: str | None = None,
    detail: dict | None = None,
    request_id: str | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    row = AuditLog(
        tenant_id=tenant_id,
        actor_id=actor_id,
        actor_email=actor_email,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        detail=detail or {},
        request_id=request_id,
        ip_address=ip_address,
        created_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def export_audit_logs(db: Session, *, tenant_id: str, limit: int = 1000) -> list[dict]:
    rows = (
        db.query(AuditLog)
        .filter(AuditLog.tenant_id == tenant_id)
        .order_by(AuditLog.created_at.asc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": str(r.id),
            "tenant_id": r.tenant_id,
            "actor_id": str(r.actor_id) if r.actor_id else None,
            "actor_email": r.actor_email,
            "action": r.action,
            "resource_type": r.resource_type,
            "resource_id": r.resource_id,
            "detail": r.detail,
            "request_id": r.request_id,
            "ip_address": r.ip_address,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
