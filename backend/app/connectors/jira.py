from __future__ import annotations

from datetime import datetime
from typing import Any

from app.connectors.base import BaseConnector, CanonicalArtifact, SyncResult


class JiraConnector(BaseConnector):
    name = "jira"

    def sync(self, *, cursor: str | None = None, limit: int = 50) -> SyncResult:
        self._require_auth()
        issues = list(self._credentials.get("issues") or [])
        start = int(cursor or 0)
        batch = issues[start : start + limit]
        artifacts = [self.normalize_issue(m) for m in batch]
        next_cursor = str(start + len(batch)) if start + len(batch) < len(issues) else None
        return SyncResult(artifacts=artifacts, next_cursor=next_cursor, stats={"count": len(artifacts)})

    @staticmethod
    def normalize_issue(raw: dict[str, Any]) -> CanonicalArtifact:
        key = raw.get("key") or raw.get("id") or "UNKNOWN"
        fields = raw.get("fields") or raw
        summary = fields.get("summary") or key
        description = fields.get("description") or ""
        if isinstance(description, dict):
            description = str(description)
        occurred = None
        if fields.get("created"):
            occurred = datetime.fromisoformat(str(fields["created"]).replace("Z", "+00:00"))
        assignee = (fields.get("assignee") or {}).get("displayName") or fields.get("assignee")
        return CanonicalArtifact(
            source_system="jira",
            source_id=str(key),
            artifact_type="issue",
            title=f"{key}: {summary}",
            content_text=f"{summary}\n\n{description}".strip(),
            source_uri=raw.get("self"),
            occurred_at=occurred,
            authors=[assignee] if assignee else [],
            acl={"principals": [], "visibility": "org"},
            raw=raw,
        )
