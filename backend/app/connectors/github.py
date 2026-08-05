from __future__ import annotations

from datetime import datetime
from typing import Any

from app.connectors.base import BaseConnector, CanonicalArtifact, SyncResult


class GitHubConnector(BaseConnector):
    name = "github"

    def sync(self, *, cursor: str | None = None, limit: int = 50) -> SyncResult:
        self._require_auth()
        items = list(self._credentials.get("items") or [])
        start = int(cursor or 0)
        batch = items[start : start + limit]
        artifacts = [self.normalize_item(m) for m in batch]
        next_cursor = str(start + len(batch)) if start + len(batch) < len(items) else None
        return SyncResult(artifacts=artifacts, next_cursor=next_cursor, stats={"count": len(artifacts)})

    @staticmethod
    def normalize_item(raw: dict[str, Any]) -> CanonicalArtifact:
        kind = raw.get("type") or "issue"
        number = raw.get("number") or raw.get("id")
        title = raw.get("title") or f"GitHub {kind} {number}"
        body = raw.get("body") or ""
        occurred = None
        if raw.get("created_at"):
            occurred = datetime.fromisoformat(str(raw["created_at"]).replace("Z", "+00:00"))
        return CanonicalArtifact(
            source_system="github",
            source_id=str(raw.get("node_id") or f"{kind}:{number}"),
            artifact_type="pr" if kind == "pull_request" else "issue",
            title=title,
            content_text=f"{title}\n\n{body}".strip(),
            source_uri=raw.get("html_url"),
            occurred_at=occurred,
            authors=[(raw.get("user") or {}).get("login") or raw.get("author") or "unknown"],
            acl={"principals": [], "visibility": "org"},
            raw=raw,
        )
