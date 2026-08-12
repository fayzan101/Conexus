"""In-process Prometheus metrics + OpenTelemetry-shaped spans (no extra deps)."""

from __future__ import annotations

import threading
import time
import uuid
from collections import defaultdict
from contextlib import contextmanager
from typing import Any, Iterator

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

_lock = threading.Lock()
_counters: dict[tuple[str, tuple[tuple[str, str], ...]], float] = defaultdict(float)
_histograms: dict[str, list[float]] = defaultdict(list)
_spans: list[dict[str, Any]] = []
_MAX_SAMPLES = 2000
_MAX_SPANS = 200


def reset_metrics() -> None:
    with _lock:
        _counters.clear()
        _histograms.clear()
        _spans.clear()


def inc(name: str, value: float = 1.0, **labels: str) -> None:
    key = (name, tuple(sorted(labels.items())))
    with _lock:
        _counters[key] += value


def observe(name: str, value: float) -> None:
    with _lock:
        samples = _histograms[name]
        samples.append(value)
        if len(samples) > _MAX_SAMPLES:
            del samples[: len(samples) - _MAX_SAMPLES]


def percentile(name: str, p: float) -> float | None:
    with _lock:
        samples = list(_histograms.get(name, []))
    if not samples:
        return None
    samples.sort()
    idx = min(len(samples) - 1, max(0, int(round((p / 100.0) * (len(samples) - 1)))))
    return samples[idx]


def counter_value(name: str, **labels: str) -> float:
    key = (name, tuple(sorted(labels.items())))
    with _lock:
        return float(_counters.get(key, 0.0))


def sum_counter(name: str) -> float:
    with _lock:
        return float(sum(v for (n, _), v in _counters.items() if n == name))


def record_request(method: str, path: str, status: int, duration_ms: float) -> None:
    route = _normalize_path(path)
    inc("eb_http_requests_total", method=method, path=route, status=str(status))
    observe("eb_http_request_duration_ms", duration_ms)
    if route.startswith("/v1/search"):
        observe("eb_search_duration_ms", duration_ms)
    if route.startswith("/v1/chat"):
        observe("eb_chat_duration_ms", duration_ms)
    if status >= 500:
        inc("eb_http_errors_total", method=method, path=route)


def record_acl_drop(reason: str, count: int = 1) -> None:
    inc("eb_acl_drop_total", float(count), reason=reason or "unknown")


def record_grounded(grounded: bool) -> None:
    inc("eb_chat_answers_total", grounded="true" if grounded else "false")


def record_queue_depth(depth: int) -> None:
    with _lock:
        _histograms["eb_ingest_queue_depth"] = [float(depth)]


def record_llm_tokens(tokens: int, *, cached: bool = False, blocked: bool = False) -> None:
    inc("eb_llm_tokens_total", float(tokens))
    if cached:
        inc("eb_llm_cache_hits_total")
    if blocked:
        inc("eb_llm_budget_blocked_total")


@contextmanager
def start_span(name: str, **attrs: Any) -> Iterator[dict[str, Any]]:
    span = {
        "id": str(uuid.uuid4()),
        "name": name,
        "attrs": attrs,
        "start": time.perf_counter(),
        "duration_ms": None,
    }
    try:
        yield span
    finally:
        span["duration_ms"] = round((time.perf_counter() - span["start"]) * 1000, 3)
        with _lock:
            _spans.append({k: v for k, v in span.items() if k != "start"})
            if len(_spans) > _MAX_SPANS:
                del _spans[: len(_spans) - _MAX_SPANS]


def recent_spans(limit: int = 20) -> list[dict[str, Any]]:
    with _lock:
        return list(_spans[-limit:])


def golden_signals() -> dict[str, Any]:
    total = sum_counter("eb_http_requests_total")
    errors = sum_counter("eb_http_errors_total")
    answers = sum_counter("eb_chat_answers_total")
    grounded = counter_value("eb_chat_answers_total", grounded="true")
    acl_drops = sum_counter("eb_acl_drop_total")
    with _lock:
        queue = list(_histograms.get("eb_ingest_queue_depth") or [0])
    return {
        "latency": {
            "http_p95_ms": percentile("eb_http_request_duration_ms", 95),
            "search_p95_ms": percentile("eb_search_duration_ms", 95),
            "chat_p95_ms": percentile("eb_chat_duration_ms", 95),
        },
        "traffic": {"http_requests": total},
        "errors": {"http_5xx": errors, "error_rate": (errors / total) if total else 0.0},
        "saturation": {"ingest_queue_depth": queue[-1] if queue else 0},
        "domain": {
            "acl_drop_total": acl_drops,
            "grounded_ratio": (grounded / answers) if answers else None,
            "llm_tokens_total": sum_counter("eb_llm_tokens_total"),
            "llm_cache_hits": sum_counter("eb_llm_cache_hits_total"),
            "llm_budget_blocked": sum_counter("eb_llm_budget_blocked_total"),
        },
    }


def render_prometheus() -> str:
    lines = [
        "# HELP eb_http_requests_total HTTP requests",
        "# TYPE eb_http_requests_total counter",
    ]
    with _lock:
        counters = list(_counters.items())
        histograms = {k: list(v) for k, v in _histograms.items()}
    for (name, labels), value in sorted(counters):
        if name != "eb_http_requests_total":
            continue
        lines.append(f"{name}{_fmt_labels(labels)} {value:.0f}")
    extra_counters = sorted({n for n, _ in counters if n != "eb_http_requests_total"})
    for name in extra_counters:
        lines.append(f"# HELP {name} {name}")
        lines.append(f"# TYPE {name} counter")
        for (n, labels), value in sorted(counters):
            if n == name:
                lines.append(f"{name}{_fmt_labels(labels)} {value:.0f}")
    for name, samples in sorted(histograms.items()):
        if not samples:
            continue
        lines.append(f"# HELP {name} {name}")
        lines.append(f"# TYPE {name} gauge")
        p95 = percentile(name, 95)
        lines.append(f"{name}_p95 {p95 if p95 is not None else 0}")
        lines.append(f"{name}_count {len(samples)}")
    return "\n".join(lines) + "\n"


def _fmt_labels(labels: tuple[tuple[str, str], ...]) -> str:
    if not labels:
        return ""
    inner = ",".join(f'{k}="{v}"' for k, v in labels)
    return "{" + inner + "}"


def _normalize_path(path: str) -> str:
    parts = path.split("?")[0].split("/")
    out = []
    for p in parts:
        if not p:
            continue
        if len(p) >= 8 and all(c in "0123456789abcdef-" for c in p.lower()):
            out.append("{id}")
        else:
            out.append(p)
    return "/" + "/".join(out) if out else "/"


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        path = request.url.path
        with start_span("http.request", path=path, method=request.method, request_id=request_id):
            response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        if path not in {"/metrics"}:
            record_request(request.method, path, response.status_code, duration_ms)
        response.headers["x-request-id"] = request_id
        return response
