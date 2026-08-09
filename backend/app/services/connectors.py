from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.config import Settings
from app.connectors.base import CanonicalArtifact
from app.connectors.registry import get_connector, list_connectors
from app.db.models import ConnectorAccount, Document, IngestJob, JobStatus, TimelineEvent
from app.services.events import get_event_bus
from app.services.memory_links import propose_links_for_document
from app.services.queue import enqueue_ingest_job


def connect_account(
    db: Session,
    *,
    provider: str,
    credentials: dict,
    display_name: str | None,
    external_account_id: str,
    user_id: UUID | None,
    tenant_id: str = "default",
    token_expires_at: datetime | None = None,
) -> ConnectorAccount:
    connector = get_connector(provider)
    connector.authenticate(credentials)
    existing = (
        db.query(ConnectorAccount)
        .filter(
            ConnectorAccount.tenant_id == tenant_id,
            ConnectorAccount.provider == provider,
            ConnectorAccount.external_account_id == external_account_id,
        )
        .first()
    )
    if existing:
        existing.credentials = credentials
        existing.display_name = display_name or existing.display_name
        existing.status = "connected"
        existing.last_error = None
        existing.token_expires_at = token_expires_at
        db.commit()
        db.refresh(existing)
        return existing

    account = ConnectorAccount(
        tenant_id=tenant_id,
        provider=provider,
        external_account_id=external_account_id,
        display_name=display_name or provider,
        status="connected",
        credentials=credentials,
        created_by=user_id,
        token_expires_at=token_expires_at,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def run_sync(db: Session, account: ConnectorAccount, settings: Settings | None = None, *, limit: int = 50) -> dict:
    connector = get_connector(account.provider)
    try:
        connector.authenticate(account.credentials or {})
        result = connector.sync(cursor=account.cursor, limit=limit)
        health = connector.health()
        account.health_ok = health.ok
        account.health_detail = health.detail
    except Exception as exc:
        account.status = "error"
        account.last_error = str(exc)
        account.health_ok = False
        account.health_detail = str(exc)
        db.commit()
        raise

    stored = 0
    for art in result.artifacts:
        doc = _persist_artifact(db, art, project_id=None, tenant_id=account.tenant_id)
        if settings and settings.connector_auto_ingest and doc.text_preview:
            job = IngestJob(
                job_type="document",
                status=JobStatus.pending,
                document_id=doc.id,
                tenant_id=account.tenant_id,
            )
            db.add(job)
            db.flush()
            enqueue_ingest_job(db, settings, job.id)
            propose_links_for_document(db, settings, tenant_id=account.tenant_id, document=doc)
        stored += 1
        if settings:
            get_event_bus(settings).publish(
                settings.kafka_topic_ingest,
                {"type": "connector.artifact", "provider": account.provider, "source_id": art.source_id},
            )

    account.cursor = result.next_cursor
    account.last_sync_at = datetime.now(timezone.utc)
    account.status = "connected"
    account.last_error = None
    db.commit()
    return {"stored": stored, "next_cursor": result.next_cursor, "stats": result.stats}


def check_account_health(db: Session, account: ConnectorAccount) -> dict:
    connector = get_connector(account.provider)
    try:
        connector.authenticate(account.credentials or {})
        health = connector.health()
    except Exception as exc:
        account.health_ok = False
        account.health_detail = str(exc)
        db.commit()
        return {
            "account_id": account.id,
            "provider": account.provider,
            "ok": False,
            "lag_seconds": None,
            "detail": str(exc),
            "status": account.status,
            "last_sync_at": account.last_sync_at,
            "last_error": account.last_error,
        }

    lag = None
    if account.last_sync_at:
        lag = (datetime.now(timezone.utc) - account.last_sync_at.replace(tzinfo=timezone.utc)).total_seconds()
    account.health_ok = health.ok
    account.health_detail = health.detail
    db.commit()
    return {
        "account_id": account.id,
        "provider": account.provider,
        "ok": health.ok,
        "lag_seconds": lag if lag is not None else health.lag_seconds,
        "detail": health.detail,
        "status": account.status,
        "last_sync_at": account.last_sync_at,
        "last_error": account.last_error,
    }


def _persist_artifact(
    db: Session,
    art: CanonicalArtifact,
    project_id: UUID | None,
    tenant_id: str = "default",
) -> Document:
    doc = Document(
        tenant_id=tenant_id,
        title=art.title[:512],
        filename=f"{art.source_system}-{art.source_id}.txt",
        content_type="text/plain",
        object_key=f"connectors/{tenant_id}/{art.source_system}/{art.source_id}",
        source_system=art.source_system,
        project_id=project_id,
        visibility=(art.acl or {}).get("visibility") or "org",
        text_preview=art.content_text[:50_000],
        search_vector=f"{art.title} {art.content_text}"[:10_000],
    )
    db.add(doc)
    db.flush()

    event = TimelineEvent(
        event_type=art.artifact_type,
        title=art.title[:512],
        summary=art.content_text[:500],
        project_id=project_id,
        occurred_at=art.occurred_at or datetime.now(timezone.utc),
        source_system=art.source_system,
        source_ref=art.source_id,
        metadata_json={"authors": art.authors, "uri": art.source_uri, "tenant_id": tenant_id},
    )
    db.add(event)
    db.flush()
    return doc


def available_providers() -> list[str]:
    return list_connectors()


def webhook_ingest(
    db: Session,
    provider: str,
    payload: dict,
    settings: Settings | None = None,
    tenant_id: str = "default",
) -> CanonicalArtifact | None:
    connector = get_connector(provider)
    normalizers = {
        "slack": getattr(connector, "normalize_message", None),
        "teams": getattr(connector, "normalize_message", None),
        "github": getattr(connector, "normalize_item", None),
        "jira": getattr(connector, "normalize_issue", None),
        "google_drive": getattr(connector, "normalize_file", None),
    }
    fn = normalizers.get(provider)
    if not fn:
        from app.connectors.email import _normalize_email

        if provider in {"outlook", "gmail"}:
            art = _normalize_email(payload, provider)
            doc = _persist_artifact(db, art, None, tenant_id=tenant_id)
            if settings and settings.connector_auto_ingest and doc.text_preview:
                job = IngestJob(
                    job_type="document",
                    status=JobStatus.pending,
                    document_id=doc.id,
                    tenant_id=tenant_id,
                )
                db.add(job)
                db.flush()
                enqueue_ingest_job(db, settings, job.id)
            db.commit()
            return art
        return None
    art = fn(payload)
    doc = _persist_artifact(db, art, None, tenant_id=tenant_id)
    if settings and settings.connector_auto_ingest and doc.text_preview:
        job = IngestJob(
            job_type="document",
            status=JobStatus.pending,
            document_id=doc.id,
            tenant_id=tenant_id,
        )
        db.add(job)
        db.flush()
        enqueue_ingest_job(db, settings, job.id)
    db.commit()
    return art
