"""Per-tenant LLM token quotas, response cache, and task-based model routing."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import LlmUsageEvent, TenantLlmQuota
from app.services.llm import synthesize_with_llm
from app.services.observability import record_llm_tokens, start_span

_cache: dict[str, str] = {}
_CACHE_MAX = 512


def reset_llm_cache() -> None:
    _cache.clear()


def estimate_tokens(query: str, evidence: list[dict]) -> int:
    blob = query + "".join((e.get("snippet") or "") + (e.get("title") or "") for e in evidence)
    return max(32, len(blob) // 4)


def route_model(settings: Settings, task: str, quota: TenantLlmQuota | None = None) -> str:
    if quota and quota.model_route:
        return quota.model_route
    task = (task or "chat").lower()
    if task == "summarize" and settings.llm_model_summarize:
        return settings.llm_model_summarize
    if task == "rerank" and settings.llm_model_rerank:
        return settings.llm_model_rerank
    return settings.llm_model


def _cache_key(tenant_id: str, query: str, evidence: list[dict], model: str) -> str:
    ids = ",".join(str(e.get("id") or "") for e in evidence)
    raw = f"{tenant_id}|{model}|{query}|{ids}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_or_create_quota(db: Session, settings: Settings, tenant_id: str) -> TenantLlmQuota:
    row = db.query(TenantLlmQuota).filter(TenantLlmQuota.tenant_id == tenant_id).first()
    if not row:
        row = TenantLlmQuota(
            tenant_id=tenant_id,
            daily_token_limit=settings.llm_budget_tokens_per_day,
            tokens_used_today=0,
            window_start=datetime.now(timezone.utc),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row
    start = row.window_start
    if start and start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    if start is None or (now - start).total_seconds() >= 86400:
        row.window_start = now
        row.tokens_used_today = 0
        db.commit()
        db.refresh(row)
    return row


def set_quota(
    db: Session,
    settings: Settings,
    tenant_id: str,
    *,
    daily_token_limit: int | None = None,
    model_route: str | None = None,
) -> TenantLlmQuota:
    row = get_or_create_quota(db, settings, tenant_id)
    if daily_token_limit is not None:
        row.daily_token_limit = daily_token_limit
    if model_route is not None:
        row.model_route = model_route or None
    db.commit()
    db.refresh(row)
    return row


def quota_snapshot(db: Session, settings: Settings, tenant_id: str) -> dict:
    row = get_or_create_quota(db, settings, tenant_id)
    remaining = max(0, row.daily_token_limit - (row.tokens_used_today or 0))
    return {
        "tenant_id": tenant_id,
        "daily_token_limit": row.daily_token_limit,
        "tokens_used_today": row.tokens_used_today,
        "remaining": remaining,
        "model_route": row.model_route or route_model(settings, "chat", row),
        "window_start": row.window_start.isoformat() if row.window_start else None,
    }


def synthesize_with_budget(
    db: Session,
    settings: Settings,
    *,
    query: str,
    evidence: list[dict],
    tenant_id: str,
    task: str = "chat",
) -> str | None:
    quota = get_or_create_quota(db, settings, tenant_id)
    model = route_model(settings, task, quota)
    tokens = estimate_tokens(query, evidence)
    key = _cache_key(tenant_id, query, evidence, model)

    if settings.llm_cache_enabled and key in _cache:
        record_llm_tokens(0, cached=True)
        db.add(
            LlmUsageEvent(
                tenant_id=tenant_id, task=task, model=model, tokens=0, cached=True, blocked=False
            )
        )
        db.commit()
        return _cache[key]

    used = quota.tokens_used_today or 0
    if used + tokens > quota.daily_token_limit:
        record_llm_tokens(tokens, blocked=True)
        db.add(
            LlmUsageEvent(
                tenant_id=tenant_id, task=task, model=model, tokens=tokens, cached=False, blocked=True
            )
        )
        db.commit()
        return None

    original = settings.llm_model
    settings.llm_model = model
    try:
        with start_span("llm.synthesize", task=task, model=model, tenant_id=tenant_id):
            answer = synthesize_with_llm(settings, query=query, evidence=evidence)
    finally:
        settings.llm_model = original

    if answer and settings.llm_cache_enabled:
        if len(_cache) >= _CACHE_MAX:
            _cache.pop(next(iter(_cache)))
        _cache[key] = answer

    if answer:
        quota.tokens_used_today = used + tokens
        record_llm_tokens(tokens)
        db.add(
            LlmUsageEvent(
                tenant_id=tenant_id, task=task, model=model, tokens=tokens, cached=False, blocked=False
            )
        )
        db.commit()
    return answer


def usage_for_tenant(db: Session, tenant_id: str, *, limit: int = 50) -> list[dict]:
    rows = (
        db.query(LlmUsageEvent)
        .filter(LlmUsageEvent.tenant_id == tenant_id)
        .order_by(LlmUsageEvent.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": str(r.id),
            "task": r.task,
            "model": r.model,
            "tokens": r.tokens,
            "cached": r.cached,
            "blocked": r.blocked,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
