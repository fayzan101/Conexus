from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Protocol


@dataclass
class CanonicalArtifact:
    """Normalized record produced by any connector before ingest."""

    source_system: str
    source_id: str
    artifact_type: str
    title: str
    content_text: str
    source_uri: str | None = None
    occurred_at: datetime | None = None
    authors: list[str] = field(default_factory=list)
    acl: dict[str, Any] = field(default_factory=lambda: {"principals": [], "visibility": "org"})
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if self.occurred_at:
            data["occurred_at"] = self.occurred_at.isoformat()
        return data


@dataclass
class ConnectorHealth:
    ok: bool
    lag_seconds: float | None = None
    detail: str = ""


@dataclass
class SyncResult:
    artifacts: list[CanonicalArtifact]
    next_cursor: str | None
    stats: dict[str, Any] = field(default_factory=dict)


class Connector(Protocol):
    name: str

    def authenticate(self, credentials: dict[str, Any]) -> None: ...

    def health(self) -> ConnectorHealth: ...

    def sync(self, *, cursor: str | None = None, limit: int = 50) -> SyncResult: ...

    def revoke(self) -> None: ...


class ConnectorAuthError(Exception):
    pass


class BaseConnector:
    name = "base"

    def __init__(self) -> None:
        self._credentials: dict[str, Any] = {}
        self._authenticated = False

    def authenticate(self, credentials: dict[str, Any]) -> None:
        token = credentials.get("access_token") or credentials.get("token")
        if not token:
            raise ConnectorAuthError(f"{self.name}: missing access_token")
        self._credentials = dict(credentials)
        self._authenticated = True

    def health(self) -> ConnectorHealth:
        if not self._authenticated:
            return ConnectorHealth(ok=False, detail="not authenticated")
        return ConnectorHealth(ok=True, lag_seconds=0.0, detail="ready")

    def revoke(self) -> None:
        self._credentials = {}
        self._authenticated = False

    def _require_auth(self) -> None:
        if not self._authenticated:
            raise ConnectorAuthError(f"{self.name}: not authenticated")
