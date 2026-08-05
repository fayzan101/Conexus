from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode

import httpx

from app.config import Settings
from app.connectors.base import BaseConnector, CanonicalArtifact, ConnectorHealth, SyncResult
from app.connectors.security import with_backoff


class SlackConnector(BaseConnector):
    name = "slack"

    def health(self) -> ConnectorHealth:
        if not self._authenticated:
            return ConnectorHealth(ok=False, detail="not authenticated")
        if self._credentials.get("messages") is not None:
            return ConnectorHealth(ok=True, lag_seconds=0.0, detail="fixture mode")
        token = self._credentials.get("access_token") or self._credentials.get("token")
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(
                    "https://slack.com/api/auth.test",
                    headers={"Authorization": f"Bearer {token}"},
                )
                data = resp.json()
                if data.get("ok"):
                    return ConnectorHealth(ok=True, lag_seconds=0.0, detail=f"team={data.get('team')}")
                return ConnectorHealth(ok=False, detail=str(data.get("error")))
        except Exception as exc:
            return ConnectorHealth(ok=False, detail=str(exc))

    def sync(self, *, cursor: str | None = None, limit: int = 50) -> SyncResult:
        self._require_auth()
        # Pilot/mock path: credentials may include "messages" fixture payload
        if "messages" in self._credentials:
            messages = list(self._credentials.get("messages") or [])
            start = int(cursor or 0)
            batch = messages[start : start + limit]
            artifacts = [self.normalize_message(m) for m in batch]
            next_cursor = str(start + len(batch)) if start + len(batch) < len(messages) else None
            return SyncResult(artifacts=artifacts, next_cursor=next_cursor, stats={"count": len(artifacts), "mode": "fixture"})

        return self._live_sync(cursor=cursor, limit=limit)

    def _live_sync(self, *, cursor: str | None, limit: int) -> SyncResult:
        token = self._credentials.get("access_token") or self._credentials.get("token")
        channel = self._credentials.get("channel_id") or self._credentials.get("channel")
        if not channel:
            raise ValueError("slack live sync requires channel_id (or use messages fixture)")

        def _call() -> dict:
            params: dict[str, Any] = {"channel": channel, "limit": min(limit, 200)}
            if cursor:
                params["cursor"] = cursor
            with httpx.Client(timeout=30.0) as client:
                resp = client.get(
                    "https://slack.com/api/conversations.history",
                    headers={"Authorization": f"Bearer {token}"},
                    params=params,
                )
                if resp.status_code == 429:
                    from app.connectors.security import RateLimitError

                    raise RateLimitError(float(resp.headers.get("Retry-After", "1")))
                resp.raise_for_status()
                data = resp.json()
                if not data.get("ok"):
                    raise RuntimeError(data.get("error") or "slack api error")
                return data

        data = with_backoff(_call)
        messages = data.get("messages") or []
        artifacts = [self.normalize_message({**m, "channel": channel}) for m in messages]
        next_cursor = (data.get("response_metadata") or {}).get("next_cursor") or None
        return SyncResult(artifacts=artifacts, next_cursor=next_cursor or None, stats={"count": len(artifacts), "mode": "live"})

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


def slack_oauth_authorize_url(settings: Settings, *, state: str) -> str:
    redirect = settings.slack_redirect_uri or f"{settings.api_base_url}/v1/connectors/slack/oauth/callback"
    params = {
        "client_id": settings.slack_client_id,
        "scope": "channels:history,channels:read,groups:history,users:read",
        "redirect_uri": redirect,
        "state": state,
    }
    return f"https://slack.com/oauth/v2/authorize?{urlencode(params)}"


def slack_oauth_exchange(settings: Settings, *, code: str) -> dict[str, Any]:
    redirect = settings.slack_redirect_uri or f"{settings.api_base_url}/v1/connectors/slack/oauth/callback"
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            "https://slack.com/api/oauth.v2.access",
            data={
                "client_id": settings.slack_client_id,
                "client_secret": settings.slack_client_secret,
                "code": code,
                "redirect_uri": redirect,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get("ok"):
            raise RuntimeError(data.get("error") or "slack oauth failed")
        return data
