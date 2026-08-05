from fastapi import APIRouter, status

from app.db.models import IngestJob, JobStatus, Meeting
from app.deps import AppSettings, CurrentUser, DbSession
from app.schemas import MeetingCreate, MeetingIngestResponse, MeetingOut
from app.services.ingest import process_meeting_job

router = APIRouter(prefix="/v1/meetings", tags=["meetings"])


@router.post("/transcripts", response_model=MeetingIngestResponse, status_code=status.HTTP_201_CREATED)
def ingest_transcript(
    payload: MeetingCreate,
    db: DbSession,
    user: CurrentUser,
    settings: AppSettings,
):
    meeting = Meeting(
        title=payload.title,
        transcript=payload.transcript,
        project_id=payload.project_id,
        occurred_at=payload.occurred_at,
        created_by=user.id,
    )
    db.add(meeting)
    db.flush()

    job = IngestJob(job_type="meeting", status=JobStatus.pending, meeting_id=meeting.id)
    db.add(job)
    db.commit()
    db.refresh(meeting)
    db.refresh(job)

    process_meeting_job(db, settings, job.id)
    db.refresh(meeting)
    db.refresh(job)

    return MeetingIngestResponse(meeting=meeting, job_id=job.id)


@router.get("", response_model=list[MeetingOut])
def list_meetings(db: DbSession, _: CurrentUser):
    return db.query(Meeting).order_by(Meeting.created_at.desc()).limit(100).all()
