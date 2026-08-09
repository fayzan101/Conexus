from __future__ import annotations

from datetime import datetime
from typing import Any
from urllib.parse import urlencode

import httpx

from app.config import Settings
from app.connectors.base import BaseConnector, CanonicalArtifact, ConnectorHealth, SyncResult
from app.connectors.security import with_backoff


class GoogleDriveConnector(BaseConnector):
    name = "google_drive"

    def health(self) -> ConnectorHealth:
        if not self._authenticated:
            return ConnectorHealth(ok=False, detail="not authenticated")
        if self._credentials.get("files") is not None:
            return ConnectorHealth(ok=True, lag_seconds=0.0, detail="fixture mode")
        token = self._credentials.get("access_token") or self._credentials.get("token")
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(
                    "https://www.googleapis.com/drive/v3/about",
                    headers={"Authorization": f"Bearer {token}"},
                    params={"fields": "user"},
                )
                if resp.status_code == 200:
                    email = ((resp.json().get("user") or {}).get("emailAddress")) or "ok"
                    return ConnectorHealth(ok=True, detail=email)
                return ConnectorHealth(ok=False, detail=f"status={resp.status_code}")
        except Exception as exc:
            return ConnectorHealth(ok=False, detail=str(exc))

    def sync(self, *, cursor: str | None = None, limit: int = 50) -> SyncResult:
        self._require_auth()
        if "files" in self._credentials:
            files = list(self._credentials.get("files") or [])
            start = int(cursor or 0)
            batch = files[start : start + limit]
            artifacts = [self.normalize_file(m) for m in batch]
            next_cursor = str(start + len(batch)) if start + len(batch) < len(files) else None
            return SyncResult(artifacts=artifacts, next_cursor=next_cursor, stats={"count": len(artifacts), "mode": "fixture"})

        token = self._credentials.get("access_token") or self._credentials.get("token")

        def _call() -> dict:
            params: dict[str, Any] = {
                "pageSize": min(limit, 100),
                "fields": "nextPageToken,files(id,name,description,modifiedTime,webViewLink,owners)",
            }
            if cursor:
                params["pageToken"] = cursor
            with httpx.Client(timeout=30.0) as client:
                resp = client.get(
                    "https://www.googleapis.com/drive/v3/files",
                    headers={"Authorization": f"Bearer {token}"},
                    params=params,
                )
                if resp.status_code == 429:
                    from app.connectors.security import RateLimitError

                    raise RateLimitError(float(resp.headers.get("Retry-After", "1")))
                resp.raise_for_status()
                return resp.json()

        data = with_backoff(_call)
        files = data.get("files") or []
        artifacts = [self.normalize_file(m) for m in files]
        return SyncResult(
            artifacts=artifacts,
            next_cursor=data.get("nextPageToken"),
            stats={"count": len(artifacts), "mode": "live"},
        )

    @staticmethod
    def normalize_file(raw: dict[str, Any]) -> CanonicalArtifact:
        file_id = raw.get("id") or raw.get("name") or "file"
        name = raw.get("name") or str(file_id)
        content = raw.get("content") or raw.get("description") or ""
        occurred = None
        if raw.get("modifiedTime"):
            occurred = datetime.fromisoformat(str(raw["modifiedTime"]).replace("Z", "+00:00"))
        authors = []
        if raw.get("owners"):
            authors = [raw.get("owners", [{}])[0].get("emailAddress")]
        return CanonicalArtifact(
            source_system="google_drive",
            source_id=str(file_id),
            artifact_type="document",
            title=name,
            content_text=f"{name}\n\n{content}".strip(),
            source_uri=raw.get("webViewLink"),
            occurred_at=occurred,
            authors=authors,
            acl={"principals": [], "visibility": raw.get("visibility") or "org"},
            raw=raw,
        )


def google_oauth_authorize_url(settings: Settings, *, state: str, scopes: str) -> str:
    redirect = settings.google_redirect_uri or f"{settings.api_base_url}/v1/connectors/google_drive/oauth/callback"
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": redirect,
        "response_type": "code",
        "scope": scopes,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"


def google_oauth_exchange(settings: Settings, *, code: str, redirect_uri: str | None = None) -> dict[str, Any]:
    redirect = redirect_uri or settings.google_redirect_uri or f"{settings.api_base_url}/v1/connectors/google_drive/oauth/callback"
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": redirect,
                "grant_type": "authorization_code",
            },
        )
        resp.raise_for_status()
        return resp.json()
