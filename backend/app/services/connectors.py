from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.connectors.base import CanonicalArtifact
from app.connectors.registry import get_connector, list_connectors
from app.db.models import ConnectorAccount, Document, TimelineEvent


def connect_account(
    db: Session,
    *,
    provider: str,
    credentials: dict,
    display_name: str | None,
    external_account_id: str,
    user_id: UUID | None,
) -> ConnectorAccount:
    connector = get_connector(provider)
    connector.authenticate(credentials)
    existing = (
        db.query(ConnectorAccount)
        .filter(
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
        db.commit()
        db.refresh(existing)
        return existing

    account = ConnectorAccount(
        provider=provider,
        external_account_id=external_account_id,
        display_name=display_name or provider,
        status="connected",
        credentials=credentials,
        created_by=user_id,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def run_sync(db: Session, account: ConnectorAccount, *, limit: int = 50) -> dict:
    connector = get_connector(account.provider)
    try:
        connector.authenticate(account.credentials or {})
        result = connector.sync(cursor=account.cursor, limit=limit)
    except Exception as exc:
        account.status = "error"
        account.last_error = str(exc)
        db.commit()
        raise

    stored = 0
    for art in result.artifacts:
        _persist_artifact(db, art, project_id=None)
        stored += 1

    account.cursor = result.next_cursor
    account.last_sync_at = datetime.now(timezone.utc)
    account.status = "connected"
    account.last_error = None
    db.commit()
    return {"stored": stored, "next_cursor": result.next_cursor, "stats": result.stats}


def _persist_artifact(db: Session, art: CanonicalArtifact, project_id: UUID | None) -> Document:
    doc = Document(
        title=art.title[:512],
        filename=f"{art.source_system}-{art.source_id}.txt",
        content_type="text/plain",
        object_key=f"connectors/{art.source_system}/{art.source_id}",
        source_system=art.source_system,
        project_id=project_id,
        visibility=(art.acl or {}).get("visibility") or "org",
        text_preview=art.content_text[:50_000],
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
        metadata_json={"authors": art.authors, "uri": art.source_uri},
    )
    db.add(event)
    db.flush()
    return doc


def available_providers() -> list[str]:
    return list_connectors()


def webhook_ingest(db: Session, provider: str, payload: dict) -> CanonicalArtifact | None:
    """Normalize a single webhook payload using the connector's static normalizer when present."""
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
        # email connectors share helper via credentials path; accept generic body
        from app.connectors.email import _normalize_email

        if provider in {"outlook", "gmail"}:
            art = _normalize_email(payload, provider)
            _persist_artifact(db, art, None)
            db.commit()
            return art
        return None
    art = fn(payload)
    _persist_artifact(db, art, None)
    db.commit()
    return art
