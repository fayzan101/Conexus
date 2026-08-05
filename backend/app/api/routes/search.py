from fastapi import APIRouter

from app.db.models import QueryLog
from app.deps import AppSettings, CurrentUser, DbSession
from app.schemas import SearchRequest, SearchResponse
from app.services.rag import semantic_search

router = APIRouter(prefix="/v1/search", tags=["search"])


@router.post("", response_model=SearchResponse)
def search(payload: SearchRequest, db: DbSession, user: CurrentUser, settings: AppSettings):
    project_id = payload.filters.project_id if payload.filters else None
    results = semantic_search(
        db,
        settings,
        query=payload.query,
        user_id=user.id,
        limit=payload.limit,
        project_id=project_id,
    )
    return SearchResponse(results=results)


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
        {"id": str(r.id), "query_type": r.query_type, "query_text": r.query_text, "created_at": r.created_at}
        for r in rows
    ]
