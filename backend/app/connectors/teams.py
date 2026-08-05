from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.connectors.base import BaseConnector, CanonicalArtifact, SyncResult


class TeamsConnector(BaseConnector):
    name = "teams"

    def sync(self, *, cursor: str | None = None, limit: int = 50) -> SyncResult:
        self._require_auth()
        messages = list(self._credentials.get("messages") or [])
        start = int(cursor or 0)
        batch = messages[start : start + limit]
        artifacts = [self.normalize_message(m) for m in batch]
        next_cursor = str(start + len(batch)) if start + len(batch) < len(messages) else None
        return SyncResult(artifacts=artifacts, next_cursor=next_cursor, stats={"count": len(artifacts)})

    @staticmethod
    def normalize_message(raw: dict[str, Any]) -> CanonicalArtifact:
        msg_id = raw.get("id") or raw.get("message_id") or "teams-msg"
        text = raw.get("body") or raw.get("content") or raw.get("text") or ""
        occurred = None
        if raw.get("createdDateTime"):
            occurred = datetime.fromisoformat(str(raw["createdDateTime"]).replace("Z", "+00:00"))
        elif raw.get("ts"):
            occurred = datetime.fromtimestamp(float(raw["ts"]), tz=timezone.utc)
        return CanonicalArtifact(
            source_system="teams",
            source_id=str(msg_id),
            artifact_type="message",
            title=raw.get("subject") or "Teams message",
            content_text=text if isinstance(text, str) else str(text),
            source_uri=raw.get("webUrl"),
            occurred_at=occurred,
            authors=[raw.get("from") or raw.get("user") or "unknown"],
            acl={"principals": [], "visibility": "org"},
            raw=raw,
        )
