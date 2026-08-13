"""SaaS billing quotas and SLA uptime commitment measurement."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import Document, SlaMeasurement, TenantBilling, User
from app.services.observability import percentile

PLAN_DEFAULTS = {
    "pilot": {"seat_limit": 25, "document_limit": 10_000, "monthly_llm_token_limit": 1_000_000},
    "growth": {"seat_limit": 100, "document_limit": 100_000, "monthly_llm_token_limit": 5_000_000},
    "enterprise": {"seat_limit": 1000, "document_limit": 1_000_000, "monthly_llm_token_limit": 50_000_000},
}


def get_or_create_billing(db: Session, settings: Settings, tenant_id: str) -> TenantBilling:
    row = db.query(TenantBilling).filter(TenantBilling.tenant_id == tenant_id).first()
    if row:
        return row
    plan = settings.billing_plan_default if settings.billing_plan_default in PLAN_DEFAULTS else "pilot"
    defaults = PLAN_DEFAULTS[plan]
    row = TenantBilling(tenant_id=tenant_id, plan=plan, **defaults)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def set_billing_plan(db: Session, settings: Settings, tenant_id: str, plan: str) -> TenantBilling:
    if plan not in PLAN_DEFAULTS:
        raise ValueError(f"Unknown plan '{plan}'")
    row = get_or_create_billing(db, settings, tenant_id)
    defaults = PLAN_DEFAULTS[plan]
    row.plan = plan
    row.seat_limit = defaults["seat_limit"]
    row.document_limit = defaults["document_limit"]
    row.monthly_llm_token_limit = defaults["monthly_llm_token_limit"]
    db.commit()
    db.refresh(row)
    return row


def billing_usage(db: Session, settings: Settings, tenant_id: str) -> dict:
    row = get_or_create_billing(db, settings, tenant_id)
    seats = db.query(func.count(User.id)).filter(User.tenant_id == tenant_id, User.is_active.is_(True)).scalar() or 0
    docs = db.query(func.count(Document.id)).filter(Document.tenant_id == tenant_id).scalar() or 0
    return {
        "tenant_id": tenant_id,
        "plan": row.plan,
        "status": row.status,
        "limits": {
            "seats": row.seat_limit,
            "documents": row.document_limit,
            "monthly_llm_tokens": row.monthly_llm_token_limit,
        },
        "usage": {"seats": int(seats), "documents": int(docs)},
        "within_limits": seats <= row.seat_limit and docs <= row.document_limit,
    }


def sla_definition(settings: Settings) -> dict:
    return {
        "uptime_target": settings.sla_uptime_target,
        "search_p95_ms": settings.slo_search_p95_ms,
        "chat_p95_ms": settings.slo_chat_p95_ms,
        "error_rate_budget": settings.slo_error_rate,
        "measurement": "Monthly calendar period; excludes customer-caused outages",
    }


def record_sla_period(
    db: Session,
    settings: Settings,
    *,
    tenant_id: str = "default",
    uptime_ratio: float | None = None,
    period_days: int = 30,
) -> SlaMeasurement:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=period_days)
    uptime = 1.0 if uptime_ratio is None else uptime_ratio
    search_p95 = percentile("eb_search_duration_ms", 95)
    chat_p95 = percentile("eb_chat_duration_ms", 95)
    met = uptime >= settings.sla_uptime_target
    if search_p95 is not None and search_p95 > settings.slo_search_p95_ms:
        met = False
    if chat_p95 is not None and chat_p95 > settings.slo_chat_p95_ms:
        met = False
    row = SlaMeasurement(
        tenant_id=tenant_id,
        period_start=start,
        period_end=end,
        uptime_ratio=uptime,
        search_p95_ms=search_p95,
        chat_p95_ms=chat_p95,
        met_commitment=met,
        notes="Auto-recorded from live SLO samples" if uptime_ratio is None else "Provided uptime sample",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
