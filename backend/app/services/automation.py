"""Policy-gated automation: notify, create_ticket, update_doc_draft."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import AutomationAction

ALLOWED_PATTERNS = {"notify", "create_ticket", "update_doc_draft"}


def policy_allows(pattern: str, payload: dict | None, settings: Settings) -> tuple[bool, str]:
    if pattern not in ALLOWED_PATTERNS:
        return False, f"pattern_not_allowed:{pattern}"
    payload = payload or {}
    if pattern == "notify" and not payload.get("channel") and not payload.get("email"):
        return False, "notify_requires_channel_or_email"
    if pattern == "create_ticket" and not payload.get("summary"):
        return False, "ticket_requires_summary"
    if pattern == "update_doc_draft" and not (payload.get("title") and payload.get("body")):
        return False, "draft_requires_title_and_body"
    if pattern in {"create_ticket", "update_doc_draft"} and settings.agent_require_hitl_writes:
        # Write-like automations still allowed when explicitly requested via this engine,
        # but must include approval_token for GA policy.
        if not payload.get("approval_token"):
            return False, "write_requires_approval_token"
    return True, "allowed"


def enqueue_automation(
    db: Session,
    settings: Settings,
    *,
    pattern: str,
    title: str,
    payload: dict | None = None,
    tenant_id: str = "default",
    created_by: UUID | None = None,
    execute_now: bool = True,
) -> AutomationAction:
    ok, reason = policy_allows(pattern, payload, settings)
    row = AutomationAction(
        tenant_id=tenant_id,
        pattern=pattern,
        title=title,
        payload=payload or {},
        status="queued" if ok else "blocked",
        policy_reason=None if ok else reason,
        created_by=created_by,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    if ok and execute_now:
        return execute_automation(db, settings, row.id)
    return row


def execute_automation(db: Session, settings: Settings, action_id: UUID) -> AutomationAction:
    row = db.get(AutomationAction, action_id)
    if not row:
        raise ValueError("Automation action not found")
    if row.status == "blocked":
        return row

    result_detail = {"pattern": row.pattern, "simulated": True}
    webhook = (settings.automation_webhook_url or "").strip()
    if webhook and row.pattern in {"notify", "create_ticket"}:
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.post(
                    webhook,
                    json={"pattern": row.pattern, "title": row.title, "payload": row.payload},
                )
                result_detail["webhook_status"] = resp.status_code
                result_detail["simulated"] = False
        except Exception as exc:
            row.status = "failed"
            row.policy_reason = f"webhook_error:{exc}"
            db.commit()
            db.refresh(row)
            return row
    else:
        # Local/dev execution: mark executed with audit-friendly detail
        result_detail["local"] = True

    payload = dict(row.payload or {})
    payload["_execution"] = result_detail
    row.payload = payload
    row.status = "executed"
    row.executed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row


def top_automation_patterns() -> list[dict]:
    return [
        {"pattern": "notify", "description": "Notify owners of stale knowledge or high delay risk"},
        {"pattern": "create_ticket", "description": "Open a tracking ticket for remediation work"},
        {"pattern": "update_doc_draft", "description": "Propose a document draft for human approval"},
    ]
