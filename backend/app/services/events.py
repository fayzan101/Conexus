from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from collections import deque
from typing import Any, Protocol

from app.config import Settings

logger = logging.getLogger(__name__)

_metrics = {
    "published": 0,
    "dropped": 0,
    "depth": 0,
    "backpressure_trips": 0,
}


class EventBus(Protocol):
    def publish(self, topic: str, payload: dict[str, Any]) -> None: ...

    def depth(self) -> int: ...


class MemoryEventBus:
    def __init__(self, max_depth: int = 10_000):
        self._q: deque[dict[str, Any]] = deque()
        self.max_depth = max_depth

    def publish(self, topic: str, payload: dict[str, Any]) -> None:
        if len(self._q) >= self.max_depth:
            _metrics["dropped"] += 1
            _metrics["backpressure_trips"] += 1
            logger.warning("event bus backpressure: dropping topic=%s", topic)
            return
        self._q.append({"topic": topic, "payload": payload})
        _metrics["published"] += 1
        _metrics["depth"] = len(self._q)

    def depth(self) -> int:
        return len(self._q)

    def drain(self, limit: int = 100) -> list[dict[str, Any]]:
        out = []
        while self._q and len(out) < limit:
            out.append(self._q.popleft())
        _metrics["depth"] = len(self._q)
        return out


class KafkaEventBus:
    """Kafka producer adapter; falls back to memory if kafka-python unavailable."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._fallback = MemoryEventBus(max_depth=settings.queue_max_depth)
        self._producer = None
        try:
            from kafka import KafkaProducer  # type: ignore

            self._producer = KafkaProducer(
                bootstrap_servers=settings.kafka_bootstrap_servers.split(","),
                value_serializer=lambda v: __import__("json").dumps(v).encode("utf-8"),
            )
        except Exception as exc:
            logger.warning("Kafka unavailable (%s); using memory event bus", exc)

    def publish(self, topic: str, payload: dict[str, Any]) -> None:
        if self._producer is None:
            self._fallback.publish(topic, payload)
            return
        try:
            self._producer.send(topic or self.settings.kafka_topic_ingest, payload)
            _metrics["published"] += 1
        except Exception as exc:
            logger.warning("Kafka publish failed (%s); memory fallback", exc)
            self._fallback.publish(topic, payload)

    def depth(self) -> int:
        return self._fallback.depth()


_bus: EventBus | None = None


def get_event_bus(settings: Settings) -> EventBus:
    global _bus
    if _bus is None:
        if settings.event_bus_backend == "kafka":
            _bus = KafkaEventBus(settings)
        else:
            _bus = MemoryEventBus(max_depth=settings.queue_max_depth)
    return _bus


def reset_event_bus() -> None:
    global _bus
    _bus = None


def event_bus_metrics() -> dict[str, int]:
    return dict(_metrics)


def wrap_dek(plaintext_dek: bytes, master_secret: str) -> str:
    digest = hmac.new(master_secret.encode("utf-8"), plaintext_dek, hashlib.sha256).hexdigest()
    return f"{plaintext_dek.hex()}:{digest}"


def ensure_tenant_key(db, settings: Settings, tenant_id: str):
    from app.db.models import TenantCryptoKey

    existing = db.query(TenantCryptoKey).filter(TenantCryptoKey.tenant_id == tenant_id).first()
    if existing:
        return existing
    dek = secrets.token_bytes(32)
    row = TenantCryptoKey(
        tenant_id=tenant_id,
        wrapped_dek=wrap_dek(dek, settings.secret_key),
        algorithm="aes-256-gcm",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
