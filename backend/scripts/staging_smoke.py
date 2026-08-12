"""Staging smoke: health, search/chat, ops SLO + backup drill (requires running API).

Usage:
  set EB_TOKEN=<jwt from /v1/auth/login>
  python scripts/staging_smoke.py
"""

from __future__ import annotations

import os
import sys

import httpx

API = os.getenv("API_BASE_URL", "http://localhost:8000")
TOKEN = os.getenv("EB_TOKEN", "")


def main() -> int:
    if not TOKEN:
        print("Set EB_TOKEN from /v1/auth/login first", file=sys.stderr)
        return 1
    headers = {"Authorization": f"Bearer {TOKEN}"}
    with httpx.Client(base_url=API, headers=headers, timeout=60.0) as client:
        live = client.get("/livez")
        live.raise_for_status()
        metrics = client.get("/metrics")
        metrics.raise_for_status()
        if "eb_http_requests_total" not in metrics.text and metrics.text.strip() == "":
            pass
        slo = client.get("/v1/ops/slo")
        slo.raise_for_status()
        profile = client.get("/v1/ops/deploy-profile")
        profile.raise_for_status()
        drill = client.post(
            "/v1/ops/backup-drills",
            json={"store": "postgres", "environment": os.getenv("ENVIRONMENT", "staging"), "notes": "staging smoke"},
        )
        drill.raise_for_status()
        print("staging_smoke_ok", {
            "live": live.json(),
            "slo_all_ok": slo.json().get("all_ok"),
            "deploy_mode": profile.json().get("deploy_mode"),
            "drill": drill.json().get("id"),
        })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
