"""Public status page + GA release metadata."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import EvalGateRun, PenTestFinding, SlaMeasurement
from app.services.observability import golden_signals
from app.services.slo import evaluate_slos


def status_page(db: Session, settings: Settings) -> dict:
    if not settings.status_page_public and settings.environment not in {"local", "test", "development"}:
        return {"error": "status_page_disabled"}

    slo = evaluate_slos(settings)
    signals = golden_signals()
    latest_sla = db.query(SlaMeasurement).order_by(SlaMeasurement.created_at.desc()).first()
    open_findings = db.query(PenTestFinding).filter(PenTestFinding.status == "open").count()
    latest_eval = db.query(EvalGateRun).order_by(EvalGateRun.created_at.desc()).first()

    components = [
        {"name": "API", "status": "operational" if slo["ok"]["error_rate"] else "degraded"},
        {
            "name": "Search",
            "status": "operational" if slo["ok"]["search_p95"] else "degraded",
        },
        {
            "name": "Assistant",
            "status": "operational" if slo["ok"]["chat_p95"] else "degraded",
        },
    ]
    overall = "operational" if all(c["status"] == "operational" for c in components) else "degraded"
    return {
        "product": "Enterprise Brain",
        "version": settings.ga_version,
        "environment": settings.environment,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "overall": overall,
        "components": components,
        "slo": slo,
        "signals": {
            "acl_drop_total": signals["domain"]["acl_drop_total"],
            "grounded_ratio": signals["domain"]["grounded_ratio"],
        },
        "sla_latest": {
            "uptime_ratio": latest_sla.uptime_ratio if latest_sla else None,
            "met_commitment": latest_sla.met_commitment if latest_sla else None,
        },
        "security": {"open_pentest_findings": int(open_findings)},
        "quality": {
            "latest_eval_suite": latest_eval.suite if latest_eval else None,
            "latest_eval_passed": latest_eval.passed if latest_eval else None,
        },
    }


def ga_readiness(db: Session, settings: Settings) -> dict:
    from app.services.compliance import compliance_pack
    from app.services.eval_gates import run_all_eval_gates

    pack = compliance_pack(db)
    gates = run_all_eval_gates(db, settings)
    return {
        "ga_version": settings.ga_version,
        "compliance_ready": pack["ready_for_ga"],
        "eval_gates_green": gates["all_passed"],
        "connectors_priority": True,
        "sso_abac_private_llm": True,
        "ready": pack["ready_for_ga"] and gates["all_passed"],
        "gates": gates,
    }
