"""Tool-allowlisted research/ops agents with human-in-the-loop write gates."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import AgentApproval, AgentRun, Prediction
from app.services.graph import GraphStore
from app.services.rag import semantic_search

WRITE_ACTIONS = {"update_doc_draft", "create_ticket", "notify", "delete_document"}


def list_allowed_tools(settings: Settings) -> list[str]:
    return list(settings.agent_tool_allowlist)


def tool_is_allowed(settings: Settings, tool: str) -> bool:
    return tool in set(settings.agent_tool_allowlist)


def _tool_search(
    db: Session,
    settings: Settings,
    problem: str,
    *,
    user_id: UUID | None,
    tenant_id: str,
) -> dict:
    if not user_id:
        return {"tool": "search", "hits": [], "error": "user_required_for_acl_search"}
    result = semantic_search(
        db,
        settings,
        query=problem,
        user_id=user_id,
        limit=5,
        tenant_id=tenant_id,
    )
    hits = [
        {
            "id": h.get("id"),
            "title": (h.get("source") or {}).get("title"),
            "snippet": h.get("snippet"),
            "score": h.get("score"),
        }
        for h in result.get("results") or []
    ]
    return {
        "tool": "search",
        "hits": hits,
        "acl_summary": result.get("acl_summary"),
        "blocked": len(result.get("blocked") or []),
    }


def _tool_graph_neighbors(settings: Settings, *, tenant_id: str, seed_id: str | None = None) -> dict:
    store = GraphStore(settings)
    try:
        node_id = seed_id or f"tenant:{tenant_id}"
        neighbors = store.neighbors(node_id, limit=10, tenant_id=tenant_id)
        if not neighbors:
            # Fall back to tenant-scoped search for any Person/Project nodes
            neighbors = store.search("Person", None, limit=5, tenant_id=tenant_id)
            neighbors += store.search("Project", None, limit=5, tenant_id=tenant_id)
        return {
            "tool": "graph_neighbors",
            "neighbors": [
                {"id": n.get("id"), "label": n.get("label"), "properties": n.get("properties")}
                for n in neighbors[:10]
            ],
        }
    except Exception as exc:
        return {"tool": "graph_neighbors", "neighbors": [], "error": str(exc)}
    finally:
        store.close()


def _tool_list_predictions(db: Session, *, tenant_id: str) -> dict:
    rows = (
        db.query(Prediction)
        .filter(Prediction.tenant_id == tenant_id)
        .order_by(Prediction.created_at.desc())
        .limit(5)
        .all()
    )
    return {
        "tool": "list_predictions",
        "items": [
            {
                "id": str(r.id),
                "type": r.prediction_type,
                "probability": r.probability,
                "title": r.title,
            }
            for r in rows
        ],
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
            used.append(_tool_search(db, settings, problem, user_id=user_id, tenant_id=tenant_id))
        elif tool == "graph_neighbors":
            used.append(_tool_graph_neighbors(settings, tenant_id=tenant_id))
        elif tool == "list_predictions":
            used.append(_tool_list_predictions(db, tenant_id=tenant_id))
        elif tool == "draft_doc":
            draft = _tool_draft_doc(problem)
            used.append(draft)
            if settings.agent_require_hitl_writes:
                pending_write = {"action_type": "update_doc_draft", "payload": draft["draft"]}
            else:
                pending_write = None
        else:
            # Fail closed on unknown tools even if somehow allowlisted
            unsafe = True
            used.append({"tool": tool, "error": "unknown_tool_fail_closed"})

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
