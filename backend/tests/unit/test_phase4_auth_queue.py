from datetime import datetime, timezone

from app.config import Settings
from app.db.models import IngestJob, JobStatus
from app.services.llm import check_faithfulness
from app.services.queue import enqueue_ingest_job, list_failed_jobs, retry_job


def test_refresh_token_roundtrip(client, test_settings):
    login = client.post(
        "/v1/auth/login",
        json={"email": test_settings.dev_admin_email, "password": test_settings.dev_admin_password},
    )
    assert login.status_code == 200
    body = login.json()
    assert body.get("refresh_token")
    refreshed = client.post("/v1/auth/refresh", json={"refresh_token": body["refresh_token"]})
    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"]


def test_invite_accept_flow(client, test_settings, auth_headers):
    created = client.post(
        "/v1/auth/invites",
        headers=auth_headers,
        json={"email": "pilot@example.com", "role": "employee"},
    )
    assert created.status_code == 200, created.text
    token = created.json()["token"]
    accepted = client.post(
        "/v1/auth/invites/accept",
        json={"token": token, "password": "securepass", "full_name": "Pilot User"},
    )
    assert accepted.status_code == 200, accepted.text
    me = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {accepted.json()['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == "pilot@example.com"


def test_dev_auth_blocked_outside_local():
    try:
        Settings(auth_provider="dev", environment="production", secret_key="x")
        assert False, "expected validation error"
    except Exception:
        pass


def test_faithfulness_requires_citations():
    assert check_faithfulness("Answer without cites", 2)["ok"] is False
    assert check_faithfulness("Answer with [1] cite", 2)["ok"] is True
    assert check_faithfulness("I could not find accessible evidence", 0)["ok"] is True


def test_queue_dead_letter_and_retry(db, test_settings, monkeypatch):
    job = IngestJob(job_type="document", status=JobStatus.pending, document_id=None, max_attempts=1)
    db.add(job)
    db.commit()
    db.refresh(job)

    def boom(db, settings, job_id, **kwargs):
        j = db.get(IngestJob, job_id)
        j.status = JobStatus.failed
        j.error = "boom"
        db.commit()
        return j

    monkeypatch.setattr("app.services.queue.process_document_job", boom)
    result = enqueue_ingest_job(db, test_settings, job.id)
    assert result.status == JobStatus.dead_lettered
    failed = list_failed_jobs(db)
    assert any(j.id == job.id for j in failed)

    def ok(db, settings, job_id, **kwargs):
        j = db.get(IngestJob, job_id)
        j.status = JobStatus.completed
        j.error = None
        db.commit()
        return j

    monkeypatch.setattr("app.services.queue.process_document_job", ok)
    retried = retry_job(db, test_settings, job.id)
    assert retried.status == JobStatus.completed
