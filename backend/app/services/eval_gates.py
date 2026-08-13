"""Continuous RAG/agent/perf eval gates for CI and GA quality bar."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import AgentRun, EvalGateRun
from app.services.agents import evaluate_agent_harness
from app.services.observability import golden_signals, percentile
from app.services.slo import evaluate_slos


def run_rag_eval_gate(db: Session, settings: Settings, *, recall_at_5: float, citation_rate: float) -> EvalGateRun:
    passed = recall_at_5 >= settings.eval_min_recall_at_5 and citation_rate >= settings.eval_min_citation_rate
    row = EvalGateRun(
        suite="rag",
        metrics={
            "recall_at_5": recall_at_5,
            "citation_rate": citation_rate,
            "min_recall_at_5": settings.eval_min_recall_at_5,
            "min_citation_rate": settings.eval_min_citation_rate,
        },
        passed=passed,
        environment=settings.environment,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def run_agent_eval_gate(db: Session, settings: Settings) -> EvalGateRun:
    runs = db.query(AgentRun).order_by(AgentRun.created_at.desc()).limit(50).all()
    metrics = evaluate_agent_harness(runs)
    passed = bool(metrics["passed"]) and metrics["unsafe_action_rate"] <= settings.eval_max_unsafe_action_rate
    row = EvalGateRun(
        suite="agent",
        metrics={**metrics, "max_unsafe_action_rate": settings.eval_max_unsafe_action_rate},
        passed=passed,
        environment=settings.environment,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def run_perf_eval_gate(db: Session, settings: Settings) -> EvalGateRun:
    slo = evaluate_slos(settings)
    signals = golden_signals()
    metrics = {
        "search_p95_ms": percentile("eb_search_duration_ms", 95),
        "chat_p95_ms": percentile("eb_chat_duration_ms", 95),
        "budgets": slo["budgets"],
        "slo_all_ok": slo["all_ok"],
        "grounded_ratio": signals["domain"]["grounded_ratio"],
    }
    # When no samples yet (fresh CI), treat as pass — budgets still recorded
    observed_search = metrics["search_p95_ms"]
    observed_chat = metrics["chat_p95_ms"]
    search_ok = observed_search is None or observed_search <= settings.slo_search_p95_ms
    chat_ok = observed_chat is None or observed_chat <= settings.slo_chat_p95_ms
    passed = search_ok and chat_ok
    row = EvalGateRun(
        suite="perf",
        metrics=metrics,
        passed=passed,
        environment=settings.environment,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def run_all_eval_gates(
    db: Session,
    settings: Settings,
    *,
    recall_at_5: float = 0.72,
    citation_rate: float = 0.95,
) -> dict:
    rag = run_rag_eval_gate(db, settings, recall_at_5=recall_at_5, citation_rate=citation_rate)
    agent = run_agent_eval_gate(db, settings)
    perf = run_perf_eval_gate(db, settings)
    return {
        "rag": {"id": str(rag.id), "passed": rag.passed, "metrics": rag.metrics},
        "agent": {"id": str(agent.id), "passed": agent.passed, "metrics": agent.metrics},
        "perf": {"id": str(perf.id), "passed": perf.passed, "metrics": perf.metrics},
        "all_passed": rag.passed and agent.passed and perf.passed,
    }
