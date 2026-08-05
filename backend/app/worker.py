"""Background ingest worker. Run: python -m app.worker"""

from __future__ import annotations

import logging
import time
from uuid import UUID

from app.config import get_settings
from app.db.session import SessionLocal
from app.services.queue import get_queue, process_queued_job

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("eb.worker")


def run_forever() -> None:
    settings = get_settings()
    # Worker must not inline-recurse; process only dequeued items
    settings.queue_inline = False
    queue = get_queue(settings)
    logger.info("Ingest worker started backend=%s", settings.queue_backend)
    while True:
        job_id = queue.dequeue(timeout=settings.worker_poll_seconds)
        if not job_id:
            continue
        db = SessionLocal()
        try:
            process_queued_job(db, settings, UUID(job_id))
            logger.info("Processed job %s", job_id)
        except Exception:
            logger.exception("Failed processing job %s", job_id)
        finally:
            db.close()


if __name__ == "__main__":
    run_forever()
