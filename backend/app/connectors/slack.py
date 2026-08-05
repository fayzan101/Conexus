from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.connectors.base import BaseConnector, CanonicalArtifact, SyncResult


class SlackConnector(BaseConnector):
    name = "slack"

    def sync(self, *, cursor: str | None = None, limit: int = 50) -> SyncResult:
        self._require_auth()
        # Pilot/mock path: credentials may include "messages" fixture payload
        messages = list(self._credentials.get("messages") or [])
        start = int(cursor or 0)
        batch = messages[start : start + limit]
        artifacts = [self.normalize_message(m) for m in batch]
        next_cursor = str(start + len(batch)) if start + len(batch) < len(messages) else None
        return SyncResult(artifacts=artifacts, next_cursor=next_cursor, stats={"count": len(artifacts)})

    @staticmethod
    def normalize_message(raw: dict[str, Any]) -> CanonicalArtifact:
        ts = raw.get("ts")
        occurred = None
        if ts:
            occurred = datetime.fromtimestamp(float(ts), tz=timezone.utc)
        text = raw.get("text") or ""
        channel = raw.get("channel") or "unknown"
        msg_id = raw.get("ts") or raw.get("client_msg_id") or text[:24]
        return CanonicalArtifact(
            source_system="slack",
            source_id=f"{channel}:{msg_id}",
            artifact_type="message",
            title=f"Slack #{channel}",
            content_text=text,
            source_uri=raw.get("permalink"),
            occurred_at=occurred,
            authors=[raw.get("user") or "unknown"],
            acl={"principals": raw.get("acl_principals") or [], "visibility": raw.get("visibility") or "org"},
            raw=raw,
        )
