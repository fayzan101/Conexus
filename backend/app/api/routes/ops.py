from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from app.db.models import Role, User
from app.deps import AppSettings, CurrentUser, DbSession, require_roles
from app.services.backup import (
    DEPLOY_MODES,
    STORES,
    deploy_matrix,
    list_chaos,
    list_drills,
    record_deploy_proof,
    record_drill,
    restore_checklist,
    rpo_rto_matrix,
    simulate_failover,
)
from app.services.events import event_bus_metrics
from app.services.llm_budget import quota_snapshot, set_quota, usage_for_tenant
from app.services.observability import golden_signals, recent_spans, record_queue_depth, render_prometheus
from app.services.queue import get_queue
from app.services.slo import evaluate_slos

router = APIRouter(tags=["ops"])
OpsAdmin = Annotated[User, Depends(require_roles(Role.admin, Role.ai_administrator))]


class QuotaUpdate(BaseModel):
    daily_token_limit: int | None = Field(default=None, ge=0)
    model_route: str | None = None
    tenant_id: str | None = None


class BackupDrillIn(BaseModel):
    store: str
    environment: str | None = None
    status: str = "passed"
    notes: str | None = None


class DeployProofIn(BaseModel):
    deploy_mode: str
    environment: str | None = None
    notes: str | None = None
    status: str = "proven"


class ChaosIn(BaseModel):
    component: str = "api"
    environment: str | None = None


@router.get("/metrics")
def prometheus_metrics(settings: AppSettings):
    if not settings.prometheus_enabled:
        raise HTTPException(status_code=404, detail="Prometheus scrape disabled")
    return Response(content=render_prometheus(), media_type="text/plain; version=0.0.4")


@router.get("/v1/ops/golden-signals")
def ops_golden_signals(_admin: OpsAdmin, settings: AppSettings):
    queue = get_queue(settings)
    depth = len(getattr(queue, "_q", [])) if hasattr(queue, "_q") else 0
    record_queue_depth(depth)
    signals = golden_signals()
    signals["event_bus"] = event_bus_metrics()
    return signals


@router.get("/v1/ops/slo")
def ops_slo(_admin: OpsAdmin, settings: AppSettings):
    return evaluate_slos(settings)


@router.get("/v1/ops/traces")
def ops_traces(_admin: OpsAdmin, limit: int = 20):
    return {"spans": recent_spans(limit=limit)}


@router.get("/v1/ops/llm-budget")
def ops_llm_budget(db: DbSession, user: CurrentUser, settings: AppSettings, tenant_id: str | None = None):
    tid = tenant_id or user.tenant_id
    if tid != user.tenant_id and user.role not in {Role.admin, Role.ai_administrator}:
        raise HTTPException(status_code=403, detail="Cannot view other tenant budgets")
    snap = quota_snapshot(db, settings, tid)
    snap["recent"] = usage_for_tenant(db, tid, limit=20)
    return snap


@router.put("/v1/ops/llm-budget")
def ops_llm_budget_update(payload: QuotaUpdate, db: DbSession, settings: AppSettings, user: OpsAdmin):
    tid = payload.tenant_id or user.tenant_id
    row = set_quota(
        db,
        settings,
        tid,
        daily_token_limit=payload.daily_token_limit,
        model_route=payload.model_route,
    )
    return quota_snapshot(db, settings, row.tenant_id)


@router.get("/v1/ops/backup")
def ops_backup_get(db: DbSession, _admin: OpsAdmin, settings: AppSettings):
    drills = list_drills(db, limit=50)
    return {
        "rpo_rto": rpo_rto_matrix(settings),
        "stores": list(STORES),
        "drills": [
            {
                "id": str(d.id),
                "store": d.store,
                "environment": d.environment,
                "rpo_hours": d.rpo_hours,
                "rto_hours": d.rto_hours,
                "status": d.status,
                "notes": d.notes,
                "performed_at": d.performed_at.isoformat() if d.performed_at else None,
            }
            for d in drills
        ],
    }


@router.post("/v1/ops/backup-drills")
def ops_backup_drill(payload: BackupDrillIn, db: DbSession, settings: AppSettings, user: OpsAdmin):
    try:
        row = record_drill(
            db,
            settings,
            store=payload.store,
            environment=payload.environment,
            status=payload.status,
            notes=payload.notes,
            performed_by=user.id,
            tenant_id=user.tenant_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "id": str(row.id),
        "store": row.store,
        "status": row.status,
        "checklist": restore_checklist(row.store),
        "rpo_hours": row.rpo_hours,
        "rto_hours": row.rto_hours,
        "performed_at": row.performed_at.isoformat() if row.performed_at else None,
    }


@router.get("/v1/ops/deploy-profile")
def ops_deploy_profile(db: DbSession, _admin: OpsAdmin, settings: AppSettings):
    return deploy_matrix(db, settings)


@router.post("/v1/ops/deploy-proofs")
def ops_deploy_proof(payload: DeployProofIn, db: DbSession, settings: AppSettings, user: OpsAdmin):
    try:
        row = record_deploy_proof(
            db,
            deploy_mode=payload.deploy_mode,
            environment=payload.environment or settings.environment,
            notes=payload.notes,
            proven_by=user.id,
            status=payload.status,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "id": str(row.id),
        "deploy_mode": row.deploy_mode,
        "environment": row.environment,
        "status": row.status,
        "modes": DEPLOY_MODES,
        "proven_at": row.proven_at.isoformat() if row.proven_at else None,
    }


@router.post("/v1/ops/chaos/failover")
def ops_chaos(payload: ChaosIn, db: DbSession, settings: AppSettings, user: OpsAdmin):
    row = simulate_failover(
        db,
        settings,
        component=payload.component,
        environment=payload.environment,
        performed_by=user.id,
    )
    return {
        "id": str(row.id),
        "component": row.component,
        "status": row.status,
        "steps": row.steps,
        "notes": row.notes,
        "performed_at": row.performed_at.isoformat() if row.performed_at else None,
    }


@router.get("/v1/ops/chaos")
def ops_chaos_list(db: DbSession, _admin: OpsAdmin):
    return [
        {
            "id": str(r.id),
            "component": r.component,
            "environment": r.environment,
            "status": r.status,
            "steps": r.steps,
            "performed_at": r.performed_at.isoformat() if r.performed_at else None,
        }
        for r in list_chaos(db)
    ]
