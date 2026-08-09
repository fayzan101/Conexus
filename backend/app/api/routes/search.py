from fastapi import APIRouter

from app.db.models import QueryLog
from app.deps import AppSettings, CurrentUser, DbSession
from app.schemas import SearchRequest, SearchResponse
from app.services.hybrid_search import hybrid_search
from app.services.rag import semantic_search

router = APIRouter(prefix="/v1/search", tags=["search"])


@router.post("", response_model=SearchResponse)
def search(payload: SearchRequest, db: DbSession, user: CurrentUser, settings: AppSettings):
    filters = payload.filters
    project_id = filters.project_id if filters else None
    blocked = []
    acl_summary = None
    blocked_reason = None
    if payload.mode == "hybrid":
        results = hybrid_search(
            db,
            settings,
            query=payload.query,
            user_id=user.id,
            limit=payload.limit,
            project_id=project_id,
            tenant_id=user.tenant_id,
            source_system=filters.source_system if filters else None,
            date_from=filters.date_from if filters else None,
            date_to=filters.date_to if filters else None,
            types=filters.types if filters else None,
            people=filters.people if filters else None,
        )
    else:
        out = semantic_search(
            db,
            settings,
            query=payload.query,
            user_id=user.id,
            limit=payload.limit,
            project_id=project_id,
            tenant_id=user.tenant_id,
        )
        results = out["results"]
        blocked = out["blocked"]
        acl_summary = out["acl_summary"]
        if not results and blocked:
            blocked_reason = (
                "Results were filtered by access policy: "
                + ", ".join(acl_summary.get("blocked_reasons") or [])
            )
    return SearchResponse(
        results=results,
        blocked=blocked or None,
        acl_summary=acl_summary,
        blocked_reason=blocked_reason,
    )


@router.get("/recent")
def recent_queries(db: DbSession, user: CurrentUser):
    rows = (
        db.query(QueryLog)
        .filter(QueryLog.user_id == user.id)
        .order_by(QueryLog.created_at.desc())
        .limit(20)
        .all()
    )
    return [
        {
            "id": str(r.id),
            "query_type": r.query_type,
            "query_text": r.query_text,
            "created_at": r.created_at,
        }
        for r in rows
    ]
