from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.db.models import TimelineEvent
from app.deps import CurrentUser, DbSession
from app.schemas import TimelineEventCreate, TimelineEventOut
from app.services.hybrid_search import project_memory

router = APIRouter(tags=["timeline"])


@router.get("/v1/timeline", response_model=list[TimelineEventOut])
def list_timeline(
    db: DbSession,
    _: CurrentUser,
    project_id: UUID | None = None,
    limit: int = 50,
):
    q = db.query(TimelineEvent)
    if project_id:
        q = q.filter(TimelineEvent.project_id == project_id)
    return q.order_by(TimelineEvent.occurred_at.desc()).limit(limit).all()


@router.post("/v1/timeline", response_model=TimelineEventOut, status_code=status.HTTP_201_CREATED)
def create_timeline_event(payload: TimelineEventCreate, db: DbSession, _: CurrentUser):
    event = TimelineEvent(**payload.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.get("/v1/projects/{project_id}/memory")
def get_project_memory(project_id: UUID, db: DbSession, _: CurrentUser):
    return project_memory(db, project_id)
