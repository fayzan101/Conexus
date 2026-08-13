"""Locked KPI definitions, trend snapshots, exportable board packs."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import (
    Decision,
    KpiDefinition,
    KpiSnapshot,
    Prediction,
    QueryLog,
    User,
)
from app.services.operating_system import executive_kpis

DEFAULT_KPIS = [
    {
        "key": "knowledge_health",
        "name": "Knowledge health",
        "description": "Composite freshness/trust/completeness score",
        "unit": "ratio",
        "target": 0.75,
        "audience": "executive",
    },
    {
        "key": "decision_velocity",
        "name": "Decision velocity",
        "description": "Decisions recorded in rolling window",
        "unit": "count",
        "target": 5.0,
        "audience": "executive",
    },
    {
        "key": "high_risk_predictions",
        "name": "High-risk predictions",
        "description": "Open high-severity predictive alerts",
        "unit": "count",
        "target": 0.0,
        "audience": "both",
    },
    {
        "key": "queries_24h",
        "name": "Queries (24h)",
        "description": "Search/chat query volume last day",
        "unit": "count",
        "target": None,
        "audience": "operator",
    },
    {
        "key": "open_recommendations",
        "name": "Open recommendations",
        "description": "Actionable recommendations awaiting owners",
        "unit": "count",
        "target": 10.0,
        "audience": "operator",
    },
]


def ensure_default_kpis(db: Session, tenant_id: str = "default") -> list[KpiDefinition]:
    rows = []
    for spec in DEFAULT_KPIS:
        existing = (
            db.query(KpiDefinition)
            .filter(KpiDefinition.tenant_id == tenant_id, KpiDefinition.key == spec["key"])
            .first()
        )
        if existing:
            rows.append(existing)
            continue
        row = KpiDefinition(tenant_id=tenant_id, **spec)
        db.add(row)
        rows.append(row)
    db.commit()
    for r in rows:
        db.refresh(r)
    return rows


def _current_values(db: Session, tenant_id: str) -> dict[str, float]:
    kpis = executive_kpis(db)
    since = datetime.now(timezone.utc)
    # reuse 24h queries via QueryLog if present
    from datetime import timedelta

    q24 = (
        db.query(func.count(QueryLog.id))
        .filter(QueryLog.tenant_id == tenant_id, QueryLog.created_at >= since - timedelta(hours=24))
        .scalar()
        or 0
    )
    return {
        "knowledge_health": float(kpis.get("knowledge_health") or 0),
        "decision_velocity": float(kpis.get("decision_velocity_proxy") or kpis.get("decision_count") or 0),
        "high_risk_predictions": float(kpis.get("high_risk_predictions") or 0),
        "queries_24h": float(q24),
        "open_recommendations": float(kpis.get("open_recommendations") or 0),
        "document_count": float(kpis.get("document_count") or 0),
        "user_count": float(db.query(func.count(User.id)).filter(User.tenant_id == tenant_id).scalar() or 0),
        "prediction_count": float(db.query(func.count(Prediction.id)).scalar() or 0),
        "decision_count": float(
            db.query(func.count(Decision.id)).filter(Decision.tenant_id == tenant_id).scalar() or 0
        ),
    }


def capture_kpi_snapshots(db: Session, tenant_id: str = "default") -> list[KpiSnapshot]:
    ensure_default_kpis(db, tenant_id)
    values = _current_values(db, tenant_id)
    created = []
    for key, value in values.items():
        if key not in {k["key"] for k in DEFAULT_KPIS} and key not in values:
            continue
        # Only persist locked KPI keys + a few extras used by board pack
        if key not in {k["key"] for k in DEFAULT_KPIS}:
            continue
        row = KpiSnapshot(tenant_id=tenant_id, kpi_key=key, value=value)
        db.add(row)
        created.append(row)
    db.commit()
    for r in created:
        db.refresh(r)
    return created


def kpi_trends(db: Session, tenant_id: str = "default", *, limit: int = 30) -> dict[str, list[dict]]:
    rows = (
        db.query(KpiSnapshot)
        .filter(KpiSnapshot.tenant_id == tenant_id)
        .order_by(KpiSnapshot.captured_at.desc())
        .limit(limit * 5)
        .all()
    )
    trends: dict[str, list[dict]] = {}
    for r in rows:
        trends.setdefault(r.kpi_key, [])
        if len(trends[r.kpi_key]) < limit:
            trends[r.kpi_key].append(
                {"value": r.value, "captured_at": r.captured_at.isoformat() if r.captured_at else None}
            )
    return trends


def board_pack(db: Session, tenant_id: str = "default", *, audience: str = "executive") -> dict:
    defs = ensure_default_kpis(db, tenant_id)
    capture_kpi_snapshots(db, tenant_id)
    values = _current_values(db, tenant_id)
    trends = kpi_trends(db, tenant_id, limit=12)
    items = []
    for d in defs:
        if audience != "both" and d.audience not in {audience, "both"}:
            continue
        items.append(
            {
                "key": d.key,
                "name": d.name,
                "unit": d.unit,
                "target": d.target,
                "value": values.get(d.key),
                "on_target": (
                    None
                    if d.target is None or values.get(d.key) is None
                    else (
                        values[d.key] >= d.target
                        if d.key != "high_risk_predictions"
                        else values[d.key] <= d.target
                    )
                ),
                "trend": list(reversed(trends.get(d.key, []))),
            }
        )
    return {
        "tenant_id": tenant_id,
        "audience": audience,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "kpis": items,
        "summary": {
            "documents": values.get("document_count"),
            "decisions": values.get("decision_count"),
            "users": values.get("user_count"),
        },
    }


def role_view(db: Session, *, role: str, tenant_id: str = "default") -> dict:
    audience = "executive" if role in {"admin", "manager", "auditor"} else "operator"
    pack = board_pack(db, tenant_id, audience=audience)
    pack["role"] = role
    pack["view"] = audience
    return pack
