from __future__ import annotations

from datetime import datetime
from typing import Any

from app.connectors.base import BaseConnector, CanonicalArtifact, SyncResult


class GoogleDriveConnector(BaseConnector):
    name = "google_drive"

    def sync(self, *, cursor: str | None = None, limit: int = 50) -> SyncResult:
        self._require_auth()
        files = list(self._credentials.get("files") or [])
        start = int(cursor or 0)
        batch = files[start : start + limit]
        artifacts = [self.normalize_file(m) for m in batch]
        next_cursor = str(start + len(batch)) if start + len(batch) < len(files) else None
        return SyncResult(artifacts=artifacts, next_cursor=next_cursor, stats={"count": len(artifacts)})

    @staticmethod
    def normalize_file(raw: dict[str, Any]) -> CanonicalArtifact:
        file_id = raw.get("id") or raw.get("name") or "file"
        name = raw.get("name") or str(file_id)
        content = raw.get("content") or raw.get("description") or ""
        occurred = None
        if raw.get("modifiedTime"):
            occurred = datetime.fromisoformat(str(raw["modifiedTime"]).replace("Z", "+00:00"))
        return CanonicalArtifact(
            source_system="google_drive",
            source_id=str(file_id),
            artifact_type="document",
            title=name,
            content_text=f"{name}\n\n{content}".strip(),
            source_uri=raw.get("webViewLink"),
            occurred_at=occurred,
            authors=[raw.get("owners", [{}])[0].get("emailAddress")] if raw.get("owners") else [],
            acl={"principals": [], "visibility": raw.get("visibility") or "org"},
            raw=raw,
        )
