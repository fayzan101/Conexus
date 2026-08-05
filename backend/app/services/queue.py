from __future__ import annotations

import json
import logging
from collections import deque
from datetime import datetime, timezone
from typing import Protocol
from uuid import UUID

from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import IngestJob, JobStatus
from app.services.ingest import process_document_job, process_meeting_job

logger = logging.getLogger(__name__)

QUEUE_KEY = "eb:ingest:queue"
DLQ_KEY = "eb:ingest:dlq"


class QueueBackend(Protocol):
    def enqueue(self, job_id: str) -> None: ...

    def dequeue(self, timeout: float = 1.0) -> str | None: ...

    def dead_letter(self, job_id: str, reason: str) -> None: ...


class MemoryQueue:
    def __init__(self) -> None:
        self._q: deque[str] = deque()
        self._dlq: list[dict] = []

    def enqueue(self, job_id: str) -> None:
        self._q.append(job_id)

    def dequeue(self, timeout: float = 1.0) -> str | None:
        if not self._q:
            return None
        return self._q.popleft()

    def dead_letter(self, job_id: str, reason: str) -> None:
        self._dlq.append({"job_id": job_id, "reason": reason})


class RedisQueue:
    def __init__(self, redis_url: str):
        import redis

        self._r = redis.Redis.from_url(redis_url, decode_responses=True)

    def enqueue(self, job_id: str) -> None:
        self._r.lpush(QUEUE_KEY, job_id)

    def dequeue(self, timeout: float = 1.0) -> str | None:
        item = self._r.brpop(QUEUE_KEY, timeout=max(1, int(timeout)))
        if not item:
            return None
        return item[1]

    def dead_letter(self, job_id: str, reason: str) -> None:
        self._r.lpush(DLQ_KEY, json.dumps({"job_id": job_id, "reason": reason}))


_memory_singleton = MemoryQueue()


def get_queue(settings: Settings) -> QueueBackend:
    if settings.queue_backend == "redis":
        try:
            return RedisQueue(settings.redis_url)
        except Exception as exc:
            logger.warning("Redis queue unavailable (%s); falling back to memory", exc)
    return _memory_singleton


def enqueue_ingest_job(
    db: Session,
    settings: Settings,
    job_id: UUID,
    *,
    process_now: bool | None = None,
) -> IngestJob:
    job = db.get(IngestJob, job_id)
    if not job:
        raise ValueError("Job not found")
    job.status = JobStatus.pending
    job.dead_lettered = False
    job.queued_at = datetime.now(timezone.utc)
    db.commit()

    queue = get_queue(settings)
    queue.enqueue(str(job_id))

    inline = settings.queue_inline if process_now is None else process_now
    if inline:
        process_queued_job(db, settings, job_id)
        db.refresh(job)
    return job


def process_queued_job(db: Session, settings: Settings, job_id: UUID) -> IngestJob:
    job = db.get(IngestJob, job_id)
    if not job:
        raise ValueError("Job not found")

    job.attempts = (job.attempts or 0) + 1
    db.commit()

    try:
        if job.job_type == "document":
            result = process_document_job(db, settings, job_id)
        elif job.job_type == "meeting":
            result = process_meeting_job(db, settings, job_id)
        else:
            job.status = JobStatus.failed
            job.error = f"Unknown job_type={job.job_type}"
            db.commit()
            result = job
    except Exception as exc:
        job.status = JobStatus.failed
        job.error = str(exc)
        db.commit()
        db.refresh(job)
        result = job

    if result.status == JobStatus.failed:
        if result.attempts >= result.max_attempts:
            result.status = JobStatus.dead_lettered
            result.dead_lettered = True
            get_queue(settings).dead_letter(str(job_id), result.error or "max attempts")
            db.commit()
        else:
            # re-queue for another attempt when not inline
            if not settings.queue_inline:
                get_queue(settings).enqueue(str(job_id))
    return result


def retry_job(db: Session, settings: Settings, job_id: UUID) -> IngestJob:
    job = db.get(IngestJob, job_id)
    if not job:
        raise ValueError("Job not found")
    job.status = JobStatus.pending
    job.dead_lettered = False
    job.error = None
    job.attempts = 0
    db.commit()
    return enqueue_ingest_job(db, settings, job_id)


def list_failed_jobs(db: Session, *, limit: int = 50) -> list[IngestJob]:
    return (
        db.query(IngestJob)
        .filter(IngestJob.status.in_([JobStatus.failed, JobStatus.dead_lettered]))
        .order_by(IngestJob.updated_at.desc())
        .limit(limit)
        .all()
    )
