from datetime import datetime, timedelta, timezone

from fastapi import APIRouter
from sqlalchemy import func

from app.db.models import Decision, Document, IngestJob, JobStatus, Meeting, QueryLog, User
from app.deps import CurrentUser, DbSession
from app.schemas import MetricsOverview

router = APIRouter(prefix="/v1/metrics", tags=["metrics"])


@router.get("/overview", response_model=MetricsOverview)
def overview(db: DbSession, _: CurrentUser):
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    return MetricsOverview(
        documents=db.query(func.count(Document.id)).scalar() or 0,
        meetings=db.query(func.count(Meeting.id)).scalar() or 0,
        decisions=db.query(func.count(Decision.id)).scalar() or 0,
        users=db.query(func.count(User.id)).scalar() or 0,
        jobs_pending=db.query(func.count(IngestJob.id))
        .filter(IngestJob.status == JobStatus.pending)
        .scalar()
        or 0,
        jobs_failed=db.query(func.count(IngestJob.id))
        .filter(IngestJob.status == JobStatus.failed)
        .scalar()
        or 0,
        queries_24h=db.query(func.count(QueryLog.id))
        .filter(QueryLog.created_at >= since)
        .scalar()
        or 0,
    )
