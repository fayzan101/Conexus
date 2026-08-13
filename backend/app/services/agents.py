"""Tool-allowlisted research/ops agents with human-in-the-loop write gates."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import AgentApproval, AgentRun, Prediction

WRITE_ACTIONS = {"update_doc_draft", "create_ticket", "notify", "delete_document"}


def list_allowed_tools(settings: Settings) -> list[str]:
    return list(settings.agent_tool_allowlist)


def tool_is_allowed(settings: Settings, tool: str) -> bool:
    return tool in set(settings.agent_tool_allowlist)


def _tool_search(problem: str) -> dict:
    return {"tool": "search", "hits": [{"title": "Evidence", "snippet": problem[:160], "id": "ev-1"}]}


def _tool_graph_neighbors() -> dict:
    return {"tool": "graph_neighbors", "neighbors": [{"id": "person:ops", "label": "Person"}]}


def _tool_list_predictions(db: Session) -> dict:
    rows = db.query(Prediction).order_by(Prediction.created_at.desc()).limit(5).all()
    return {
        "tool": "list_predictions",
        "items": [{"id": str(r.id), "type": r.prediction_type, "probability": r.probability} for r in rows],
    }


def _tool_draft_doc(problem: str) -> dict:
    return {
        "tool": "draft_doc",
        "draft": {
            "title": f"Draft: {problem[:60]}",
            "body": f"Proposed update based on investigation of: {problem}",
        },
    }


def run_agent(
    db: Session,
    settings: Settings,
    *,
    problem: str,
    agent_type: str = "research",
    tenant_id: str = "default",
    user_id: UUID | None = None,
    requested_tools: list[str] | None = None,
) -> AgentRun:
    """LangGraph-shaped linear agent: plan → allowlisted tools → optional HITL write."""
    tools = requested_tools or ["search", "graph_neighbors", "list_predictions"]
    used: list[dict] = []
    unsafe = False
    pending_write: dict | None = None

    for tool in tools:
        if not tool_is_allowed(settings, tool):
            unsafe = True
            used.append({"tool": tool, "error": "not_in_allowlist"})
            continue
        if tool == "search":
            used.append(_tool_search(problem))
        elif tool == "graph_neighbors":
            used.append(_tool_graph_neighbors())
        elif tool == "list_predictions":
            used.append(_tool_list_predictions(db))
        elif tool == "draft_doc":
            draft = _tool_draft_doc(problem)
            used.append(draft)
            if settings.agent_require_hitl_writes:
                pending_write = {"action_type": "update_doc_draft", "payload": draft["draft"]}
            else:
                pending_write = None
        else:
            used.append({"tool": tool, "error": "unimplemented"})

    citations = []
    for step in used:
        for hit in step.get("hits") or []:
            citations.append({"id": hit.get("id"), "title": hit.get("title")})

    status = "completed"
    if pending_write and settings.agent_require_hitl_writes:
        status = "awaiting_approval"

    run = AgentRun(
        tenant_id=tenant_id,
        agent_type=agent_type,
        problem=problem,
        status=status,
        tools_used=used,
        citations=citations,
        result={
            "summary": f"Investigated '{problem}' with {len(used)} tool step(s).",
            "recommendation": "Review evidence and approve any write actions.",
        },
        unsafe_attempted=unsafe,
        created_by=user_id,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    if pending_write and settings.agent_require_hitl_writes:
        approval = AgentApproval(
            tenant_id=tenant_id,
            agent_run_id=run.id,
            action_type=pending_write["action_type"],
            payload=pending_write["payload"],
            status="pending",
            requested_by=user_id,
        )
        db.add(approval)
        db.commit()

    return run


def decide_approval(
    db: Session,
    approval_id: UUID,
    *,
    approve: bool,
    decided_by: UUID | None,
) -> AgentApproval:
    row = db.get(AgentApproval, approval_id)
    if not row:
        raise ValueError("Approval not found")
    if row.status != "pending":
        raise ValueError("Approval already decided")
    row.status = "approved" if approve else "rejected"
    row.decided_by = decided_by
    row.decided_at = datetime.now(timezone.utc)
    if row.agent_run_id:
        run = db.get(AgentRun, row.agent_run_id)
        if run:
            run.status = "completed" if approve else "rejected"
            result = dict(run.result or {})
            result["write_action"] = row.status
            run.result = result
    db.commit()
    db.refresh(row)
    return row


def evaluate_agent_harness(runs: list[AgentRun]) -> dict:
    """Task success, citation fidelity, unsafe-action rate."""
    if not runs:
        return {
            "task_success_rate": 1.0,
            "citation_fidelity": 1.0,
            "unsafe_action_rate": 0.0,
            "n": 0,
            "passed": True,
        }
    success = sum(1 for r in runs if r.status in {"completed", "awaiting_approval"}) / len(runs)
    cited = sum(1 for r in runs if r.citations) / len(runs)
    unsafe = sum(1 for r in runs if r.unsafe_attempted) / len(runs)
    return {
        "task_success_rate": round(success, 3),
        "citation_fidelity": round(cited, 3),
        "unsafe_action_rate": round(unsafe, 3),
        "n": len(runs),
        "passed": success >= 0.8 and cited >= 0.5 and unsafe <= 0.05,
    }
