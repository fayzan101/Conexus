from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.db.models import AgentApproval, AgentRun, AutomationAction, Role, User
from app.deps import AppSettings, CurrentUser, DbSession, require_roles
from app.services.agents import decide_approval, list_allowed_tools, run_agent
from app.services.automation import enqueue_automation, top_automation_patterns
from app.services.billing import billing_usage, record_sla_period, set_billing_plan, sla_definition
from app.services.compliance import close_pentest_finding, compliance_pack, upsert_pentest_finding
from app.services.eval_gates import run_all_eval_gates
from app.services.executive_ga import board_pack, capture_kpi_snapshots, ensure_default_kpis, role_view
from app.services.ml_models import (
    forecast_query_volume,
    rank_experts_calibrated,
    record_expert_feedback,
    run_offline_model_evals,
    score_knowledge_entities,
    score_project_delay,
)
from app.services.status_page import ga_readiness, status_page
from app.db.models import Project

router = APIRouter(tags=["ga"])
GaAdmin = Annotated[User, Depends(require_roles(Role.admin, Role.ai_administrator, Role.manager))]


class ExpertFeedbackIn(BaseModel):
    person_key: str
    label: int = Field(ge=-1, le=1)
    topic: str | None = None


class AgentRunIn(BaseModel):
    problem: str = Field(min_length=3)
    agent_type: str = "research"
    tools: list[str] | None = None


class ApprovalDecisionIn(BaseModel):
    approve: bool


class AutomationIn(BaseModel):
    pattern: str
    title: str
    payload: dict | None = None
    execute_now: bool = True


class BillingPlanIn(BaseModel):
    plan: str
    tenant_id: str | None = None


class PenTestIn(BaseModel):
    title: str
    severity: str = "medium"
    owner: str | None = None
    remediation: str | None = None
    status: str = "open"


class PenTestCloseIn(BaseModel):
    status: str = "remediated"
    remediation: str | None = None


class SlaRecordIn(BaseModel):
    uptime_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    period_days: int = Field(default=30, ge=1, le=90)
    tenant_id: str | None = None


class EvalRunIn(BaseModel):
    recall_at_5: float = Field(default=0.72, ge=0.0, le=1.0)
    citation_rate: float = Field(default=0.95, ge=0.0, le=1.0)


@router.get("/v1/status")
def public_status(db: DbSession, settings: AppSettings):
    return status_page(db, settings)


@router.get("/v1/ga/readiness")
def readiness(db: DbSession, settings: AppSettings, _admin: GaAdmin):
    return ga_readiness(db, settings)


@router.post("/v1/ml/evals/run")
def ml_evals_run(db: DbSession, user: CurrentUser):
    rows = run_offline_model_evals(db, tenant_id=user.tenant_id)
    return [
        {
            "id": str(r.id),
            "model_name": r.model_name,
            "metrics": r.metrics,
            "passed": r.passed,
            "notes": r.notes,
        }
        for r in rows
    ]


@router.get("/v1/ml/forecast")
def ml_forecast(db: DbSession, _: CurrentUser, days: int = 7):
    return forecast_query_volume(db, days=days)


@router.get("/v1/ml/knowledge-risks")
def ml_knowledge_risks(db: DbSession, _: CurrentUser, limit: int = 20):
    return score_knowledge_entities(db, limit=limit)


@router.get("/v1/ml/project-delay/{project_id}")
def ml_project_delay(project_id: UUID, db: DbSession, _: CurrentUser):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return score_project_delay(db, project)


@router.get("/v1/experts/ranked")
def experts_ranked(db: DbSession, _: CurrentUser, topic: str | None = None, limit: int = 10):
    return rank_experts_calibrated(db, topic=topic, limit=limit)


@router.post("/v1/experts/feedback")
def experts_feedback(payload: ExpertFeedbackIn, db: DbSession, user: CurrentUser):
    try:
        row = record_expert_feedback(
            db,
            tenant_id=user.tenant_id,
            person_key=payload.person_key,
            label=payload.label,
            topic=payload.topic,
            created_by=user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"id": str(row.id), "person_key": row.person_key, "label": row.label}


@router.get("/v1/agents/tools")
def agent_tools(settings: AppSettings, _: CurrentUser):
    return {"allowlist": list_allowed_tools(settings)}


@router.post("/v1/agents/run")
def agents_run(payload: AgentRunIn, db: DbSession, user: CurrentUser, settings: AppSettings):
    run = run_agent(
        db,
        settings,
        problem=payload.problem,
        agent_type=payload.agent_type,
        tenant_id=user.tenant_id,
        user_id=user.id,
        requested_tools=payload.tools,
    )
    return {
        "id": str(run.id),
        "status": run.status,
        "tools_used": run.tools_used,
        "citations": run.citations,
        "result": run.result,
        "unsafe_attempted": run.unsafe_attempted,
    }


@router.get("/v1/agents/runs")
def agents_list(db: DbSession, user: CurrentUser, limit: int = 20):
    rows = (
        db.query(AgentRun)
        .filter(AgentRun.tenant_id == user.tenant_id)
        .order_by(AgentRun.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": str(r.id),
            "agent_type": r.agent_type,
            "problem": r.problem,
            "status": r.status,
            "unsafe_attempted": r.unsafe_attempted,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.get("/v1/agents/approvals")
def approvals_list(db: DbSession, user: CurrentUser):
    rows = (
        db.query(AgentApproval)
        .filter(AgentApproval.tenant_id == user.tenant_id)
        .order_by(AgentApproval.created_at.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "id": str(r.id),
            "action_type": r.action_type,
            "status": r.status,
            "payload": r.payload,
            "agent_run_id": str(r.agent_run_id) if r.agent_run_id else None,
        }
        for r in rows
    ]


@router.post("/v1/agents/approvals/{approval_id}/decide")
def approvals_decide(
    approval_id: UUID,
    payload: ApprovalDecisionIn,
    db: DbSession,
    user: Annotated[User, Depends(require_roles(Role.admin, Role.manager, Role.ai_administrator))],
):
    try:
        row = decide_approval(db, approval_id, approve=payload.approve, decided_by=user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"id": str(row.id), "status": row.status, "decided_at": row.decided_at.isoformat() if row.decided_at else None}


@router.get("/v1/automation/patterns")
def automation_patterns(_: CurrentUser):
    return top_automation_patterns()


@router.post("/v1/automation/actions")
def automation_create(payload: AutomationIn, db: DbSession, user: CurrentUser, settings: AppSettings):
    row = enqueue_automation(
        db,
        settings,
        pattern=payload.pattern,
        title=payload.title,
        payload=payload.payload,
        tenant_id=user.tenant_id,
        created_by=user.id,
        execute_now=payload.execute_now,
    )
    return {
        "id": str(row.id),
        "pattern": row.pattern,
        "status": row.status,
        "policy_reason": row.policy_reason,
        "payload": row.payload,
    }


@router.get("/v1/automation/actions")
def automation_list(db: DbSession, user: CurrentUser, limit: int = 50):
    rows = (
        db.query(AutomationAction)
        .filter(AutomationAction.tenant_id == user.tenant_id)
        .order_by(AutomationAction.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": str(r.id),
            "pattern": r.pattern,
            "title": r.title,
            "status": r.status,
            "policy_reason": r.policy_reason,
        }
        for r in rows
    ]


@router.get("/v1/executive/kpis")
def executive_kpis_list(db: DbSession, user: CurrentUser):
    rows = ensure_default_kpis(db, user.tenant_id)
    return [
        {
            "key": r.key,
            "name": r.name,
            "unit": r.unit,
            "target": r.target,
            "audience": r.audience,
            "description": r.description,
        }
        for r in rows
    ]


@router.post("/v1/executive/kpis/snapshot")
def executive_kpi_snapshot(db: DbSession, user: CurrentUser):
    rows = capture_kpi_snapshots(db, user.tenant_id)
    return [{"kpi_key": r.kpi_key, "value": r.value} for r in rows]


@router.get("/v1/executive/board-pack")
def executive_board_pack(db: DbSession, user: CurrentUser, audience: str = "executive"):
    return board_pack(db, user.tenant_id, audience=audience)


@router.get("/v1/executive/view")
def executive_role_view(db: DbSession, user: CurrentUser):
    return role_view(db, role=user.role.value, tenant_id=user.tenant_id)


@router.post("/v1/evals/run")
def evals_run(payload: EvalRunIn, db: DbSession, settings: AppSettings, _admin: GaAdmin):
    return run_all_eval_gates(
        db, settings, recall_at_5=payload.recall_at_5, citation_rate=payload.citation_rate
    )


@router.get("/v1/compliance/pack")
def compliance_get(db: DbSession, settings: AppSettings, _admin: GaAdmin):
    return compliance_pack(db, settings)


@router.post("/v1/compliance/pentest")
def pentest_create(payload: PenTestIn, db: DbSession, _admin: GaAdmin):
    row = upsert_pentest_finding(
        db,
        title=payload.title,
        severity=payload.severity,
        owner=payload.owner,
        remediation=payload.remediation,
        status=payload.status,
    )
    return {"id": str(row.id), "status": row.status, "title": row.title}


@router.post("/v1/compliance/pentest/{finding_id}/close")
def pentest_close(finding_id: UUID, payload: PenTestCloseIn, db: DbSession, _admin: GaAdmin):
    try:
        row = close_pentest_finding(
            db, finding_id, status=payload.status, remediation=payload.remediation
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"id": str(row.id), "status": row.status, "closed_at": row.closed_at.isoformat() if row.closed_at else None}


@router.get("/v1/billing")
def billing_get(db: DbSession, user: CurrentUser, settings: AppSettings):
    return billing_usage(db, settings, user.tenant_id)


@router.put("/v1/billing/plan")
def billing_plan(payload: BillingPlanIn, db: DbSession, settings: AppSettings, user: GaAdmin):
    tid = payload.tenant_id or user.tenant_id
    try:
        row = set_billing_plan(db, settings, tid, payload.plan)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return billing_usage(db, settings, row.tenant_id)


@router.get("/v1/sla")
def sla_get(settings: AppSettings, _: CurrentUser):
    return sla_definition(settings)


@router.post("/v1/sla/measurements")
def sla_measure(payload: SlaRecordIn, db: DbSession, settings: AppSettings, user: GaAdmin):
    row = record_sla_period(
        db,
        settings,
        tenant_id=payload.tenant_id or user.tenant_id,
        uptime_ratio=payload.uptime_ratio,
        period_days=payload.period_days,
    )
    return {
        "id": str(row.id),
        "uptime_ratio": row.uptime_ratio,
        "met_commitment": row.met_commitment,
        "search_p95_ms": row.search_p95_ms,
        "chat_p95_ms": row.chat_p95_ms,
    }
