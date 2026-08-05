from __future__ import annotations

from datetime import datetime
from typing import Any
from urllib.parse import urlencode

import httpx

from app.config import Settings
from app.connectors.base import BaseConnector, CanonicalArtifact, ConnectorHealth, SyncResult
from app.connectors.security import with_backoff


class GitHubConnector(BaseConnector):
    name = "github"

    def health(self) -> ConnectorHealth:
        if not self._authenticated:
            return ConnectorHealth(ok=False, detail="not authenticated")
        if self._credentials.get("items") is not None:
            return ConnectorHealth(ok=True, lag_seconds=0.0, detail="fixture mode")
        token = self._credentials.get("access_token") or self._credentials.get("token")
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(
                    "https://api.github.com/user",
                    headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
                )
                if resp.status_code == 200:
                    login = resp.json().get("login")
                    return ConnectorHealth(ok=True, lag_seconds=0.0, detail=f"user={login}")
                return ConnectorHealth(ok=False, detail=f"status={resp.status_code}")
        except Exception as exc:
            return ConnectorHealth(ok=False, detail=str(exc))

    def sync(self, *, cursor: str | None = None, limit: int = 50) -> SyncResult:
        self._require_auth()
        if "items" in self._credentials:
            items = list(self._credentials.get("items") or [])
            start = int(cursor or 0)
            batch = items[start : start + limit]
            artifacts = [self.normalize_item(m) for m in batch]
            next_cursor = str(start + len(batch)) if start + len(batch) < len(items) else None
            return SyncResult(artifacts=artifacts, next_cursor=next_cursor, stats={"count": len(artifacts), "mode": "fixture"})

        return self._live_sync(cursor=cursor, limit=limit)

    def _live_sync(self, *, cursor: str | None, limit: int) -> SyncResult:
        token = self._credentials.get("access_token") or self._credentials.get("token")
        owner = self._credentials.get("owner")
        repo = self._credentials.get("repo")
        if not owner or not repo:
            raise ValueError("github live sync requires owner and repo (or use items fixture)")

        page = int(cursor or 1)

        def _call() -> list[dict]:
            with httpx.Client(timeout=30.0) as client:
                resp = client.get(
                    f"https://api.github.com/repos/{owner}/{repo}/issues",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/vnd.github+json",
                    },
                    params={"state": "all", "per_page": min(limit, 100), "page": page},
                )
                if resp.status_code == 429:
                    from app.connectors.security import RateLimitError

                    raise RateLimitError(float(resp.headers.get("Retry-After", "1")))
                resp.raise_for_status()
                return resp.json()

        items = with_backoff(_call)
        artifacts = [self.normalize_item(m) for m in items]
        next_cursor = str(page + 1) if len(items) >= min(limit, 100) else None
        return SyncResult(artifacts=artifacts, next_cursor=next_cursor, stats={"count": len(artifacts), "mode": "live"})

    @staticmethod
    def normalize_item(raw: dict[str, Any]) -> CanonicalArtifact:
        kind = raw.get("type") or ("pull_request" if raw.get("pull_request") else "issue")
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


def github_oauth_authorize_url(settings: Settings, *, state: str) -> str:
    redirect = settings.github_redirect_uri or f"{settings.api_base_url}/v1/connectors/github/oauth/callback"
    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": redirect,
        "scope": "repo read:user",
        "state": state,
    }
    return f"https://github.com/login/oauth/authorize?{urlencode(params)}"


def github_oauth_exchange(settings: Settings, *, code: str) -> dict[str, Any]:
    redirect = settings.github_redirect_uri or f"{settings.api_base_url}/v1/connectors/github/oauth/callback"
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            json={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
                "redirect_uri": redirect,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("error"):
            raise RuntimeError(data.get("error_description") or data["error"])
        return data
