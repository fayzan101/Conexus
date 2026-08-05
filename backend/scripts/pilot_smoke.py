"""Pilot smoke script for Phase 1 exit path (requires running API).

Usage:
  set EB_TOKEN=<jwt from /v1/auth/login>
  python scripts/pilot_smoke.py
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
        health = client.get("/healthz")
        health.raise_for_status()
        project = client.post("/v1/projects", json={"name": f"Pilot-{os.getpid()}", "description": "smoke"})
        project.raise_for_status()
        files = {"file": ("smoke.txt", b"Project Smoke Decision: ship MVP with citations.", "text/plain")}
        doc = client.post("/v1/documents", files=files, data={"title": "Smoke doc"})
        doc.raise_for_status()
        search = client.post("/v1/search", json={"query": "MVP citations", "limit": 5})
        search.raise_for_status()
        session = client.post("/v1/chat/sessions")
        session.raise_for_status()
        sid = session.json()["id"]
        chat = client.post(f"/v1/chat/sessions/{sid}/messages", json={"content": "What was decided about MVP?"})
        chat.raise_for_status()
        print("pilot_smoke_ok", {
            "project": project.json()["id"],
            "document": doc.json()["document"]["id"],
            "search_hits": len(search.json()["results"]),
            "chat_confidence": chat.json().get("confidence"),
        })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
