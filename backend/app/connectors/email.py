from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from app.connectors.base import BaseConnector, CanonicalArtifact, ConnectorHealth, SyncResult
from app.connectors.security import with_backoff


def _normalize_email(raw: dict[str, Any], source_system: str) -> CanonicalArtifact:
    msg_id = raw.get("id") or raw.get("message_id") or raw.get("subject") or "email"
    subject = raw.get("subject") or "(no subject)"
    body = raw.get("body") or raw.get("snippet") or ""
    if isinstance(body, dict):
        body = body.get("content") or body.get("text") or str(body)
    occurred = None
    if raw.get("date"):
        occurred = datetime.fromisoformat(str(raw["date"]).replace("Z", "+00:00"))
    elif raw.get("receivedDateTime"):
        occurred = datetime.fromisoformat(str(raw["receivedDateTime"]).replace("Z", "+00:00"))
    elif raw.get("internalDate"):
        occurred = datetime.fromtimestamp(int(raw["internalDate"]) / 1000.0)
    author = raw.get("from") or "unknown"
    if isinstance(author, dict):
        author = (author.get("emailAddress") or {}).get("address") or author.get("address") or "unknown"
    return CanonicalArtifact(
        source_system=source_system,
        source_id=str(msg_id),
        artifact_type="email",
        title=subject,
        content_text=f"{subject}\n\n{body}".strip(),
        source_uri=raw.get("web_link") or raw.get("webLink"),
        occurred_at=occurred,
        authors=[author] if isinstance(author, str) else ["unknown"],
        acl={"principals": raw.get("to") or [], "visibility": "private"},
        raw=raw,
    )


class OutlookConnector(BaseConnector):
    name = "outlook"

    def health(self) -> ConnectorHealth:
        if not self._authenticated:
            return ConnectorHealth(ok=False, detail="not authenticated")
        if self._credentials.get("messages") is not None:
            return ConnectorHealth(ok=True, detail="fixture mode")
        token = self._credentials.get("access_token") or self._credentials.get("token")
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(
                    "https://graph.microsoft.com/v1.0/me",
                    headers={"Authorization": f"Bearer {token}"},
                )
                if resp.status_code == 200:
                    return ConnectorHealth(ok=True, detail=resp.json().get("mail") or "ok")
                return ConnectorHealth(ok=False, detail=f"status={resp.status_code}")
        except Exception as exc:
            return ConnectorHealth(ok=False, detail=str(exc))

    def sync(self, *, cursor: str | None = None, limit: int = 50) -> SyncResult:
        self._require_auth()
        if "messages" in self._credentials:
            messages = list(self._credentials.get("messages") or [])
            start = int(cursor or 0)
            batch = messages[start : start + limit]
            artifacts = [_normalize_email(m, "outlook") for m in batch]
            next_cursor = str(start + len(batch)) if start + len(batch) < len(messages) else None
            return SyncResult(artifacts=artifacts, next_cursor=next_cursor, stats={"count": len(artifacts), "mode": "fixture"})

        token = self._credentials.get("access_token") or self._credentials.get("token")

        def _call() -> dict:
            url = "https://graph.microsoft.com/v1.0/me/messages"
            params: dict[str, Any] = {"$top": min(limit, 50), "$select": "id,subject,bodyPreview,from,receivedDateTime,webLink"}
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
        messages = []
        for m in data.get("value") or []:
            messages.append(
                {
                    "id": m.get("id"),
                    "subject": m.get("subject"),
                    "body": m.get("bodyPreview"),
                    "from": m.get("from"),
                    "receivedDateTime": m.get("receivedDateTime"),
                    "webLink": m.get("webLink"),
                }
            )
        artifacts = [_normalize_email(m, "outlook") for m in messages]
        return SyncResult(
            artifacts=artifacts,
            next_cursor=data.get("@odata.nextLink"),
            stats={"count": len(artifacts), "mode": "live"},
        )


class GmailConnector(BaseConnector):
    name = "gmail"

    def health(self) -> ConnectorHealth:
        if not self._authenticated:
            return ConnectorHealth(ok=False, detail="not authenticated")
        if self._credentials.get("messages") is not None:
            return ConnectorHealth(ok=True, detail="fixture mode")
        token = self._credentials.get("access_token") or self._credentials.get("token")
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(
                    "https://gmail.googleapis.com/gmail/v1/users/me/profile",
                    headers={"Authorization": f"Bearer {token}"},
                )
                if resp.status_code == 200:
                    return ConnectorHealth(ok=True, detail=resp.json().get("emailAddress") or "ok")
                return ConnectorHealth(ok=False, detail=f"status={resp.status_code}")
        except Exception as exc:
            return ConnectorHealth(ok=False, detail=str(exc))

    def sync(self, *, cursor: str | None = None, limit: int = 50) -> SyncResult:
        self._require_auth()
        if "messages" in self._credentials:
            messages = list(self._credentials.get("messages") or [])
            start = int(cursor or 0)
            batch = messages[start : start + limit]
            artifacts = [_normalize_email(m, "gmail") for m in batch]
            next_cursor = str(start + len(batch)) if start + len(batch) < len(messages) else None
            return SyncResult(artifacts=artifacts, next_cursor=next_cursor, stats={"count": len(artifacts), "mode": "fixture"})

        token = self._credentials.get("access_token") or self._credentials.get("token")

        def _list() -> dict:
            params: dict[str, Any] = {"maxResults": min(limit, 50)}
            if cursor:
                params["pageToken"] = cursor
            with httpx.Client(timeout=30.0) as client:
                resp = client.get(
                    "https://gmail.googleapis.com/gmail/v1/users/me/messages",
                    headers={"Authorization": f"Bearer {token}"},
                    params=params,
                )
                if resp.status_code == 429:
                    from app.connectors.security import RateLimitError

                    raise RateLimitError(float(resp.headers.get("Retry-After", "1")))
                resp.raise_for_status()
                return resp.json()

        listing = with_backoff(_list)
        artifacts = []
        with httpx.Client(timeout=30.0) as client:
            for item in (listing.get("messages") or [])[:limit]:
                mid = item.get("id")
                resp = client.get(
                    f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{mid}",
                    headers={"Authorization": f"Bearer {token}"},
                    params={"format": "metadata", "metadataHeaders": ["Subject", "From", "Date"]},
                )
                if resp.status_code != 200:
                    continue
                data = resp.json()
                headers = {h["name"]: h["value"] for h in (data.get("payload") or {}).get("headers") or []}
                artifacts.append(
                    _normalize_email(
                        {
                            "id": mid,
                            "subject": headers.get("Subject"),
                            "from": headers.get("From"),
                            "snippet": data.get("snippet"),
                            "internalDate": data.get("internalDate"),
                        },
                        "gmail",
                    )
                )
        return SyncResult(
            artifacts=artifacts,
            next_cursor=listing.get("nextPageToken"),
            stats={"count": len(artifacts), "mode": "live"},
        )
