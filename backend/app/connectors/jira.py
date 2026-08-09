from __future__ import annotations

from datetime import datetime
from typing import Any
from urllib.parse import urlencode

import httpx

from app.config import Settings
from app.connectors.base import BaseConnector, CanonicalArtifact, ConnectorHealth, SyncResult
from app.connectors.security import with_backoff


class JiraConnector(BaseConnector):
    name = "jira"

    def health(self) -> ConnectorHealth:
        if not self._authenticated:
            return ConnectorHealth(ok=False, detail="not authenticated")
        if self._credentials.get("issues") is not None:
            return ConnectorHealth(ok=True, lag_seconds=0.0, detail="fixture mode")
        token = self._credentials.get("access_token") or self._credentials.get("token")
        base = self._credentials.get("base_url")
        if not base:
            return ConnectorHealth(ok=False, detail="missing base_url")
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(
                    f"{base.rstrip('/')}/rest/api/3/myself",
                    headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                )
                if resp.status_code == 200:
                    return ConnectorHealth(ok=True, detail=resp.json().get("displayName", "ok"))
                return ConnectorHealth(ok=False, detail=f"status={resp.status_code}")
        except Exception as exc:
            return ConnectorHealth(ok=False, detail=str(exc))

    def sync(self, *, cursor: str | None = None, limit: int = 50) -> SyncResult:
        self._require_auth()
        if "issues" in self._credentials:
            issues = list(self._credentials.get("issues") or [])
            start = int(cursor or 0)
            batch = issues[start : start + limit]
            artifacts = [self.normalize_issue(m) for m in batch]
            next_cursor = str(start + len(batch)) if start + len(batch) < len(issues) else None
            return SyncResult(artifacts=artifacts, next_cursor=next_cursor, stats={"count": len(artifacts), "mode": "fixture"})

        token = self._credentials.get("access_token") or self._credentials.get("token")
        base = self._credentials.get("base_url")
        if not base:
            raise ValueError("jira live sync requires base_url (or issues fixture)")
        start_at = int(cursor or 0)

        def _call() -> dict:
            with httpx.Client(timeout=30.0) as client:
                resp = client.get(
                    f"{base.rstrip('/')}/rest/api/3/search",
                    headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                    params={"startAt": start_at, "maxResults": min(limit, 50), "jql": "order by updated DESC"},
                )
                if resp.status_code == 429:
                    from app.connectors.security import RateLimitError

                    raise RateLimitError(float(resp.headers.get("Retry-After", "1")))
                resp.raise_for_status()
                return resp.json()

        data = with_backoff(_call)
        issues = data.get("issues") or []
        artifacts = [self.normalize_issue(m) for m in issues]
        next_cursor = str(start_at + len(issues)) if len(issues) >= min(limit, 50) else None
        return SyncResult(artifacts=artifacts, next_cursor=next_cursor, stats={"count": len(artifacts), "mode": "live"})

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


def jira_oauth_authorize_url(settings: Settings, *, state: str) -> str:
    redirect = settings.jira_redirect_uri or f"{settings.api_base_url}/v1/connectors/jira/oauth/callback"
    params = {
        "audience": "api.atlassian.com",
        "client_id": settings.jira_client_id,
        "scope": "read:jira-work read:jira-user offline_access",
        "redirect_uri": redirect,
        "state": state,
        "response_type": "code",
        "prompt": "consent",
    }
    return f"https://auth.atlassian.com/authorize?{urlencode(params)}"


def jira_oauth_exchange(settings: Settings, *, code: str) -> dict[str, Any]:
    redirect = settings.jira_redirect_uri or f"{settings.api_base_url}/v1/connectors/jira/oauth/callback"
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            "https://auth.atlassian.com/oauth/token",
            json={
                "grant_type": "authorization_code",
                "client_id": settings.jira_client_id,
                "client_secret": settings.jira_client_secret,
                "code": code,
                "redirect_uri": redirect,
            },
        )
        resp.raise_for_status()
        return resp.json()
