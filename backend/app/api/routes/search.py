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
    if payload.mode == "hybrid":
        results = hybrid_search(
            db,
            settings,
            query=payload.query,
            user_id=user.id,
            limit=payload.limit,
            project_id=project_id,
            source_system=filters.source_system if filters else None,
            date_from=filters.date_from if filters else None,
            date_to=filters.date_to if filters else None,
            types=filters.types if filters else None,
            people=filters.people if filters else None,
        )
    else:
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
        {
            "id": str(r.id),
            "query_type": r.query_type,
            "query_text": r.query_text,
            "created_at": r.created_at,
        }
        for r in rows
    ]
