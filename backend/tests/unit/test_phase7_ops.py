from app.services.llm_budget import (
    estimate_tokens,
    quota_snapshot,
    reset_llm_cache,
    route_model,
    set_quota,
    synthesize_with_budget,
)
from app.services.observability import (
    record_request,
    reset_metrics,
)
from app.services.slo import evaluate_slos


def test_prometheus_and_golden_signals(client, auth_headers):
    reset_metrics()
    record_request("GET", "/v1/search", 200, 120)
    record_request("POST", "/v1/chat/sessions/abc", 500, 40)
    text = client.get("/metrics").text
    assert "eb_http_requests_total" in text
    signals = client.get("/v1/ops/golden-signals", headers=auth_headers).json()
    assert signals["traffic"]["http_requests"] >= 1
    assert "acl_drop_total" in signals["domain"]
    slo = client.get("/v1/ops/slo", headers=auth_headers).json()
    assert "budgets" in slo
    assert "all_ok" in slo


def test_ops_forbidden_for_employee(client, user_headers):
    res = client.get("/v1/ops/slo", headers=user_headers)
    assert res.status_code == 403


def test_llm_budget_blocks_and_caches(db, test_settings, monkeypatch):
    reset_llm_cache()
    set_quota(db, test_settings, "default", daily_token_limit=50)
    evidence = [{"id": "1", "title": "RFC", "snippet": "ship the MVP with citations " * 20}]
    assert estimate_tokens("why mvp?", evidence) > 50

    called = {"n": 0}

    def fake_synth(settings, *, query, evidence):
        called["n"] += 1
        return "Based on evidence [1]"

    monkeypatch.setattr("app.services.llm_budget.synthesize_with_llm", fake_synth)
    blocked = synthesize_with_budget(
        db, test_settings, query="why mvp?", evidence=evidence, tenant_id="default"
    )
    assert blocked is None
    snap = quota_snapshot(db, test_settings, "default")
    assert snap["tokens_used_today"] == 0

    set_quota(db, test_settings, "default", daily_token_limit=100_000)
    first = synthesize_with_budget(
        db, test_settings, query="why mvp?", evidence=evidence, tenant_id="default"
    )
    second = synthesize_with_budget(
        db, test_settings, query="why mvp?", evidence=evidence, tenant_id="default"
    )
    assert first == "Based on evidence [1]"
    assert second == first
    assert called["n"] == 1
    snap = quota_snapshot(db, test_settings, "default")
    assert snap["tokens_used_today"] > 0


def test_model_routing(test_settings):
    test_settings.llm_model = "gpt-4o-mini"
    test_settings.llm_model_summarize = "gpt-4o-mini-cheap"
    assert route_model(test_settings, "summarize") == "gpt-4o-mini-cheap"
    assert route_model(test_settings, "chat") == "gpt-4o-mini"


def test_llm_budget_tenant_isolation(db, test_settings, monkeypatch):
    reset_llm_cache()
    monkeypatch.setattr(
        "app.services.llm_budget.synthesize_with_llm",
        lambda settings, *, query, evidence: "ok [1]",
    )
    set_quota(db, test_settings, "alpha", daily_token_limit=10)
    set_quota(db, test_settings, "beta", daily_token_limit=100_000)
    evidence = [{"id": "1", "title": "t", "snippet": "x" * 80}]
    a = synthesize_with_budget(db, test_settings, query="q", evidence=evidence, tenant_id="alpha")
    b = synthesize_with_budget(db, test_settings, query="q", evidence=evidence, tenant_id="beta")
    assert a is None
    assert b == "ok [1]"


def test_backup_drill_and_deploy_proof(client, auth_headers):
    res = client.post(
        "/v1/ops/backup-drills",
        headers=auth_headers,
        json={"store": "postgres", "environment": "staging", "notes": "PITR restore to staging"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["store"] == "postgres"
    assert body["status"] == "passed"
    assert any("PITR" in step or "readyz" in step for step in body["checklist"])

    listed = client.get("/v1/ops/backup", headers=auth_headers).json()
    assert listed["drills"]
    assert "postgres" in listed["rpo_rto"]

    proof = client.post(
        "/v1/ops/deploy-proofs",
        headers=auth_headers,
        json={"deploy_mode": "single_tenant", "environment": "staging", "notes": "dedicated ns"},
    )
    assert proof.status_code == 200, proof.text
    profile = client.get("/v1/ops/deploy-profile", headers=auth_headers).json()
    assert profile["modes"]["single_tenant"]["tested"] is True
    assert profile["deploy_mode"] in {"saas", "single_tenant", "private_vpc"}


def test_chaos_failover_records_steps(client, auth_headers):
    res = client.post(
        "/v1/ops/chaos/failover",
        headers=auth_headers,
        json={"component": "api", "environment": "staging"},
    )
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "passed"
    assert res.json()["steps"]
    listed = client.get("/v1/ops/chaos", headers=auth_headers).json()
    assert listed[0]["component"] == "api"


def test_slo_pageable_when_errors_high():
    reset_metrics()
    for _ in range(10):
        record_request("GET", "/v1/search", 500, 50)
    from app.config import Settings

    settings = Settings(environment="test", slo_error_rate=0.01, slo_search_p95_ms=800, slo_chat_p95_ms=2500)
    result = evaluate_slos(settings)
    assert result["ok"]["error_rate"] is False
    assert result["pageable"] is True


def test_livez_alias(client):
    assert client.get("/livez").json()["status"] == "ok"
    assert client.get("/healthz").json()["status"] == "ok"


def test_llm_budget_api(client, auth_headers):
    res = client.put(
        "/v1/ops/llm-budget",
        headers=auth_headers,
        json={"daily_token_limit": 25000, "model_route": "gpt-4o-mini"},
    )
    assert res.status_code == 200, res.text
    got = client.get("/v1/ops/llm-budget", headers=auth_headers).json()
    assert got["daily_token_limit"] == 25000
    assert got["model_route"] == "gpt-4o-mini"


def test_backup_unknown_store_400(client, auth_headers):
    res = client.post("/v1/ops/backup-drills", headers=auth_headers, json={"store": "oracle"})
    assert res.status_code == 400
