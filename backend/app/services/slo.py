"""SLO evaluation against golden-signal samples and configured budgets."""

from __future__ import annotations

from app.config import Settings
from app.services.observability import golden_signals


def evaluate_slos(settings: Settings) -> dict:
    signals = golden_signals()
    latency = signals["latency"]
    error_rate = signals["errors"]["error_rate"]
    search_p95 = latency["search_p95_ms"]
    chat_p95 = latency["chat_p95_ms"]

    search_ok = search_p95 is None or search_p95 <= settings.slo_search_p95_ms
    chat_ok = chat_p95 is None or chat_p95 <= settings.slo_chat_p95_ms
    error_ok = error_rate <= settings.slo_error_rate
    return {
        "environment": settings.environment,
        "budgets": {
            "search_p95_ms": settings.slo_search_p95_ms,
            "chat_p95_ms": settings.slo_chat_p95_ms,
            "error_rate": settings.slo_error_rate,
        },
        "observed": {
            "search_p95_ms": search_p95,
            "chat_p95_ms": chat_p95,
            "http_p95_ms": latency["http_p95_ms"],
            "error_rate": error_rate,
            "ingest_queue_depth": signals["saturation"]["ingest_queue_depth"],
            "acl_drop_total": signals["domain"]["acl_drop_total"],
            "grounded_ratio": signals["domain"]["grounded_ratio"],
        },
        "ok": {
            "search_p95": search_ok,
            "chat_p95": chat_ok,
            "error_rate": error_ok,
        },
        "all_ok": search_ok and chat_ok and error_ok,
        "pageable": (not error_ok) or (search_p95 is not None and not search_ok),
    }
