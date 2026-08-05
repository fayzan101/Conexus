from __future__ import annotations

import hashlib
import hmac
import time
from typing import Callable, TypeVar

import httpx

T = TypeVar("T")


class RateLimitError(Exception):
    def __init__(self, retry_after: float = 1.0):
        self.retry_after = retry_after
        super().__init__(f"rate limited; retry after {retry_after}s")


def with_backoff(fn: Callable[[], T], *, retries: int = 3, base_delay: float = 0.5) -> T:
    delay = base_delay
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            return fn()
        except RateLimitError as exc:
            last_exc = exc
            time.sleep(exc.retry_after or delay)
            delay *= 2
        except httpx.HTTPStatusError as exc:
            last_exc = exc
            if exc.response.status_code == 429:
                retry_after = float(exc.response.headers.get("Retry-After", delay))
                time.sleep(retry_after)
                delay *= 2
                continue
            if exc.response.status_code >= 500 and attempt < retries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            raise
    if last_exc:
        raise last_exc
    raise RuntimeError("with_backoff failed")


def verify_slack_signature(*, signing_secret: str, timestamp: str, body: bytes, signature: str) -> bool:
    if not signing_secret or not signature or not timestamp:
        return False
    try:
        ts = int(timestamp)
    except ValueError:
        return False
    if abs(time.time() - ts) > 60 * 5:
        return False
    basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
    digest = hmac.new(signing_secret.encode("utf-8"), basestring.encode("utf-8"), hashlib.sha256).hexdigest()
    expected = f"v0={digest}"
    return hmac.compare_digest(expected, signature)


def verify_github_signature(*, secret: str, body: bytes, signature_header: str) -> bool:
    if not secret or not signature_header or not signature_header.startswith("sha256="):
        return False
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    expected = f"sha256={digest}"
    return hmac.compare_digest(expected, signature_header)
