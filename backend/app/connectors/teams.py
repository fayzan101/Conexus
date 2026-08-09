from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode

import httpx

from app.config import Settings
from app.connectors.base import BaseConnector, CanonicalArtifact, ConnectorHealth, SyncResult
from app.connectors.security import with_backoff


class TeamsConnector(BaseConnector):
    name = "teams"

    def health(self) -> ConnectorHealth:
        if not self._authenticated:
            return ConnectorHealth(ok=False, detail="not authenticated")
        if self._credentials.get("messages") is not None:
            return ConnectorHealth(ok=True, lag_seconds=0.0, detail="fixture mode")
        token = self._credentials.get("access_token") or self._credentials.get("token")
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(
                    "https://graph.microsoft.com/v1.0/me",
                    headers={"Authorization": f"Bearer {token}"},
                )
                if resp.status_code == 200:
                    return ConnectorHealth(ok=True, detail=resp.json().get("userPrincipalName", "ok"))
                return ConnectorHealth(ok=False, detail=f"status={resp.status_code}")
        except Exception as exc:
            return ConnectorHealth(ok=False, detail=str(exc))

    def sync(self, *, cursor: str | None = None, limit: int = 50) -> SyncResult:
        self._require_auth()
        if "messages" in self._credentials:
            messages = list(self._credentials.get("messages") or [])
            start = int(cursor or 0)
            batch = messages[start : start + limit]
            artifacts = [self.normalize_message(m) for m in batch]
            next_cursor = str(start + len(batch)) if start + len(batch) < len(messages) else None
            return SyncResult(artifacts=artifacts, next_cursor=next_cursor, stats={"count": len(artifacts), "mode": "fixture"})

        token = self._credentials.get("access_token") or self._credentials.get("token")
        team_id = self._credentials.get("team_id")
        channel_id = self._credentials.get("channel_id")
        if not team_id or not channel_id:
            raise ValueError("teams live sync requires team_id and channel_id (or messages fixture)")

        def _call() -> dict:
            url = f"https://graph.microsoft.com/v1.0/teams/{team_id}/channels/{channel_id}/messages"
            params = {"$top": min(limit, 50)}
            if cursor:
                url = cursor
                params = {}
            with httpx.Client(timeout=30.0) as client:
                resp = client.get(url, headers={"Authorization": f"Bearer {token}"}, params=params)
                if resp.status_code == 429:
                    from app.connectors.security import RateLimitError

                    raise RateLimitError(float(resp.headers.get("Retry-After", "1")))
                resp.raise_for_status()
                return resp.json()

        data = with_backoff(_call)
        messages = data.get("value") or []
        artifacts = [self.normalize_message(m) for m in messages]
        next_cursor = data.get("@odata.nextLink")
        return SyncResult(artifacts=artifacts, next_cursor=next_cursor, stats={"count": len(artifacts), "mode": "live"})

    @staticmethod
    def normalize_message(raw: dict[str, Any]) -> CanonicalArtifact:
        msg_id = raw.get("id") or raw.get("message_id") or "teams-msg"
        body = raw.get("body") or {}
        text = body.get("content") if isinstance(body, dict) else raw.get("content") or raw.get("text") or ""
        occurred = None
        if raw.get("createdDateTime"):
            occurred = datetime.fromisoformat(str(raw["createdDateTime"]).replace("Z", "+00:00"))
        elif raw.get("ts"):
            occurred = datetime.fromtimestamp(float(raw["ts"]), tz=timezone.utc)
        from_user = raw.get("from") or {}
        if isinstance(from_user, dict):
            author = (from_user.get("user") or {}).get("displayName") or from_user.get("emailAddress") or "unknown"
        else:
            author = str(from_user)
        return CanonicalArtifact(
            source_system="teams",
            source_id=str(msg_id),
            artifact_type="message",
            title=raw.get("subject") or "Teams message",
            content_text=text if isinstance(text, str) else str(text),
            source_uri=raw.get("webUrl"),
            occurred_at=occurred,
            authors=[author],
            acl={"principals": [], "visibility": "org"},
            raw=raw,
        )


def ms_oauth_authorize_url(settings: Settings, *, state: str, scopes: str) -> str:
    redirect = settings.ms_redirect_uri or f"{settings.api_base_url}/v1/connectors/teams/oauth/callback"
    params = {
        "client_id": settings.ms_client_id,
        "response_type": "code",
        "redirect_uri": redirect,
        "response_mode": "query",
        "scope": scopes,
        "state": state,
    }
    tenant = settings.ms_tenant_id or "common"
    return f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize?{urlencode(params)}"


def ms_oauth_exchange(settings: Settings, *, code: str, redirect_uri: str | None = None) -> dict[str, Any]:
    redirect = redirect_uri or settings.ms_redirect_uri or f"{settings.api_base_url}/v1/connectors/teams/oauth/callback"
    tenant = settings.ms_tenant_id or "common"
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
            data={
                "client_id": settings.ms_client_id,
                "client_secret": settings.ms_client_secret,
                "code": code,
                "redirect_uri": redirect,
                "grant_type": "authorization_code",
            },
        )
        resp.raise_for_status()
        return resp.json()
