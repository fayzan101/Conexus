from __future__ import annotations

from datetime import datetime
from typing import Any

from app.connectors.base import BaseConnector, CanonicalArtifact, SyncResult


def _normalize_email(raw: dict[str, Any], source_system: str) -> CanonicalArtifact:
    msg_id = raw.get("id") or raw.get("message_id") or raw.get("subject") or "email"
    subject = raw.get("subject") or "(no subject)"
    body = raw.get("body") or raw.get("snippet") or ""
    occurred = None
    if raw.get("date"):
        occurred = datetime.fromisoformat(str(raw["date"]).replace("Z", "+00:00"))
    return CanonicalArtifact(
        source_system=source_system,
        source_id=str(msg_id),
        artifact_type="email",
        title=subject,
        content_text=f"{subject}\n\n{body}".strip(),
        source_uri=raw.get("web_link"),
        occurred_at=occurred,
        authors=[raw.get("from") or "unknown"],
        acl={"principals": raw.get("to") or [], "visibility": "private"},
        raw=raw,
    )


class OutlookConnector(BaseConnector):
    name = "outlook"

    def sync(self, *, cursor: str | None = None, limit: int = 50) -> SyncResult:
        self._require_auth()
        messages = list(self._credentials.get("messages") or [])
        start = int(cursor or 0)
        batch = messages[start : start + limit]
        artifacts = [_normalize_email(m, "outlook") for m in batch]
        next_cursor = str(start + len(batch)) if start + len(batch) < len(messages) else None
        return SyncResult(artifacts=artifacts, next_cursor=next_cursor, stats={"count": len(artifacts)})


class GmailConnector(BaseConnector):
    name = "gmail"

    def sync(self, *, cursor: str | None = None, limit: int = 50) -> SyncResult:
        self._require_auth()
        messages = list(self._credentials.get("messages") or [])
        start = int(cursor or 0)
        batch = messages[start : start + limit]
        artifacts = [_normalize_email(m, "gmail") for m in batch]
        next_cursor = str(start + len(batch)) if start + len(batch) < len(messages) else None
        return SyncResult(artifacts=artifacts, next_cursor=next_cursor, stats={"count": len(artifacts)})
