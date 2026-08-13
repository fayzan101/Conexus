"""Phase 8 GA maturity — unit and API expectations."""

from __future__ import annotations

from uuid import UUID

from app.db.models import ExpertiseSignal, Project
from app.services.agents import evaluate_agent_harness, run_agent, tool_is_allowed
from app.services.automation import enqueue_automation, policy_allows
from app.services.billing import billing_usage, record_sla_period, set_billing_plan, sla_definition
from app.services.compliance import close_pentest_finding, compliance_pack, upsert_pentest_finding
from app.services.eval_gates import run_all_eval_gates
from app.services.executive_ga import board_pack, capture_kpi_snapshots, ensure_default_kpis, role_view
from app.services.ml_models import (
    calibrated_delay_risk,
    calibrated_knowledge_loss,
    calibrated_overload,
    forecast_query_volume,
    logistic,
    rank_experts_calibrated,
    record_expert_feedback,
    run_offline_model_evals,
)
from app.services.status_page import ga_readiness, status_page


def test_logistic_and_calibrated_models_order_risk():
    assert 0.0 < logistic(0) < 1.0
    low = calibrated_delay_risk(docs=20, meetings=10, failed_jobs=0)
    high = calibrated_delay_risk(docs=0, meetings=0, failed_jobs=5)
    assert high["probability"] > low["probability"]
    assert high["severity"] in {"medium", "high"}

    kl_low = calibrated_knowledge_loss(freshness=0.9, trust=0.9, risk=0.1)
    kl_high = calibrated_knowledge_loss(freshness=0.1, trust=0.3, risk=0.9)
    assert kl_high["probability"] > kl_low["probability"]

    ov = calibrated_overload(open_queries=50, pending_jobs=20, users=2)
    assert ov["probability"] > 0.5


def test_offline_model_evals_and_forecast(db, test_settings):
    rows = run_offline_model_evals(db, tenant_id="default")
    names = {r.model_name for r in rows}
    assert "delay_logistic_v1" in names
    assert "expert_feedback_v1" in names
    assert "query_volume_ma_v1" in names
    assert all(r.passed for r in rows if r.model_name == "delay_logistic_v1")
    fc = forecast_query_volume(db, days=5)
    assert len(fc["forecast"]) == 5
    assert "mae" in fc["backtest"]


def test_expert_ranking_uses_feedback(db, test_settings):
    db.add(ExpertiseSignal(person_key="alice", topic="auth", weight=1.0, evidence="wrote SSO"))
    db.add(ExpertiseSignal(person_key="bob", topic="auth", weight=1.2, evidence="reviewed SAML"))
    db.commit()
    record_expert_feedback(db, tenant_id="default", person_key="alice", label=1, topic="auth")
    record_expert_feedback(db, tenant_id="default", person_key="bob", label=-1, topic="auth")
    ranked = rank_experts_calibrated(db, topic="auth", limit=5)
    assert ranked[0]["person"] == "alice"
    assert ranked[0]["model"] == "expert_feedback_v1"


def test_agent_allowlist_and_hitl(db, test_settings, seeded_db):
    assert tool_is_allowed(test_settings, "search") is True
    assert tool_is_allowed(test_settings, "delete_document") is False

    run = run_agent(
        db,
        test_settings,
        problem="Why are deployments delayed?",
        requested_tools=["search", "draft_doc", "delete_document"],
        tenant_id="default",
    )
    assert run.unsafe_attempted is True
    assert run.status == "awaiting_approval"
    assert run.citations

    # approve flow via API fixtures below; harness metrics
    metrics = evaluate_agent_harness([run])
    assert metrics["n"] == 1
    assert metrics["citation_fidelity"] == 1.0


def test_agent_api_and_approval(client, auth_headers, test_settings):
    tools = client.get("/v1/agents/tools", headers=auth_headers).json()
    assert "search" in tools["allowlist"]

    res = client.post(
        "/v1/agents/run",
        headers=auth_headers,
        json={"problem": "Investigate knowledge loss risk", "tools": ["search", "draft_doc"]},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "awaiting_approval"

    approvals = client.get("/v1/agents/approvals", headers=auth_headers).json()
    assert approvals
    pending = approvals[0]
    decided = client.post(
        f"/v1/agents/approvals/{pending['id']}/decide",
        headers=auth_headers,
        json={"approve": True},
    )
    assert decided.status_code == 200, decided.text
    assert decided.json()["status"] == "approved"


def test_automation_policy_gates(db, test_settings):
    ok, reason = policy_allows("notify", {"email": "a@b.com"}, test_settings)
    assert ok and reason == "allowed"
    blocked, why = policy_allows("create_ticket", {"summary": "fix ACL"}, test_settings)
    assert blocked is False
    assert "approval_token" in why

    row = enqueue_automation(
        db,
        test_settings,
        pattern="notify",
        title="Stale doc alert",
        payload={"email": "ops@example.com"},
        execute_now=True,
    )
    assert row.status == "executed"

    ticket = enqueue_automation(
        db,
        test_settings,
        pattern="create_ticket",
        title="Open ticket",
        payload={"summary": "Fix delay risk", "approval_token": "ok"},
        execute_now=True,
    )
    assert ticket.status == "executed"

    bad = enqueue_automation(
        db,
        test_settings,
        pattern="explode",
        title="nope",
        payload={},
        execute_now=True,
    )
    assert bad.status == "blocked"


def test_automation_api(client, auth_headers):
    patterns = client.get("/v1/automation/patterns", headers=auth_headers).json()
    assert {p["pattern"] for p in patterns} >= {"notify", "create_ticket", "update_doc_draft"}
    res = client.post(
        "/v1/automation/actions",
        headers=auth_headers,
        json={"pattern": "notify", "title": "Ping owners", "payload": {"channel": "#ops"}},
    )
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "executed"


def test_executive_kpis_and_board_pack(db, test_settings):
    defs = ensure_default_kpis(db, "default")
    assert len(defs) >= 5
    snaps = capture_kpi_snapshots(db, "default")
    assert snaps
    pack = board_pack(db, "default", audience="executive")
    assert pack["kpis"]
    assert all(k["key"] for k in pack["kpis"])
    op_view = role_view(db, role="employee", tenant_id="default")
    assert op_view["view"] == "operator"


def test_executive_api(client, auth_headers):
    kpis = client.get("/v1/executive/kpis", headers=auth_headers).json()
    assert any(k["key"] == "knowledge_health" for k in kpis)
    snap = client.post("/v1/executive/kpis/snapshot", headers=auth_headers)
    assert snap.status_code == 200
    pack = client.get("/v1/executive/board-pack", headers=auth_headers).json()
    assert "kpis" in pack
    view = client.get("/v1/executive/view", headers=auth_headers).json()
    assert view["view"] in {"executive", "operator"}


def test_eval_gates_pass_with_good_metrics(db, test_settings):
    result = run_all_eval_gates(db, test_settings, recall_at_5=0.8, citation_rate=0.95)
    assert result["rag"]["passed"] is True
    assert result["perf"]["passed"] is True
    assert "all_passed" in result


def test_eval_gates_fail_low_recall(db, test_settings):
    result = run_all_eval_gates(db, test_settings, recall_at_5=0.1, citation_rate=0.95)
    assert result["rag"]["passed"] is False
    assert result["all_passed"] is False


def test_evals_api(client, auth_headers):
    res = client.post(
        "/v1/evals/run",
        headers=auth_headers,
        json={"recall_at_5": 0.8, "citation_rate": 0.96},
    )
    assert res.status_code == 200, res.text
    assert res.json()["rag"]["passed"] is True


def test_compliance_pack_and_pentest_lifecycle(db, test_settings):
    pack = compliance_pack(db)
    assert pack["soc2_controls"]
    assert pack["gdpr"]["dpa_template"]["version"] == "1.0.0"
    assert pack["ready_for_ga"] is True

    finding = upsert_pentest_finding(db, title="Open redirect", severity="high")
    pack2 = compliance_pack(db)
    assert pack2["ready_for_ga"] is False
    closed = close_pentest_finding(db, finding.id, status="remediated", remediation="Fixed allowlist")
    assert closed.status == "remediated"
    assert compliance_pack(db)["ready_for_ga"] is True


def test_compliance_api(client, auth_headers):
    pack = client.get("/v1/compliance/pack", headers=auth_headers).json()
    assert "soc2_controls" in pack
    created = client.post(
        "/v1/compliance/pentest",
        headers=auth_headers,
        json={"title": "XSS in search", "severity": "medium"},
    )
    assert created.status_code == 200, created.text
    fid = created.json()["id"]
    closed = client.post(
        f"/v1/compliance/pentest/{fid}/close",
        headers=auth_headers,
        json={"status": "accepted", "remediation": "Accepted with WAF"},
    )
    assert closed.status_code == 200
    assert closed.json()["status"] == "accepted"


def test_billing_and_sla(db, test_settings):
    usage = billing_usage(db, test_settings, "default")
    assert usage["plan"] in {"pilot", "growth", "enterprise"}
    assert usage["within_limits"] is True
    row = set_billing_plan(db, test_settings, "default", "growth")
    assert row.seat_limit == 100
    sla = sla_definition(test_settings)
    assert sla["uptime_target"] >= 0.99
    measured = record_sla_period(db, test_settings, tenant_id="default", uptime_ratio=0.9995)
    assert measured.met_commitment is True
    failed = record_sla_period(db, test_settings, tenant_id="default", uptime_ratio=0.90)
    assert failed.met_commitment is False


def test_billing_sla_api(client, auth_headers):
    billing = client.get("/v1/billing", headers=auth_headers).json()
    assert "limits" in billing
    plan = client.put("/v1/billing/plan", headers=auth_headers, json={"plan": "enterprise"})
    assert plan.status_code == 200, plan.text
    assert plan.json()["plan"] == "enterprise"
    sla = client.get("/v1/sla", headers=auth_headers).json()
    assert "uptime_target" in sla
    measured = client.post(
        "/v1/sla/measurements",
        headers=auth_headers,
        json={"uptime_ratio": 0.999},
    )
    assert measured.status_code == 200, measured.text
    assert measured.json()["met_commitment"] is True


def test_status_page_and_ga_readiness(db, test_settings, client, auth_headers):
    # close any open findings from other tests in this module's db session first via API pack
    status = client.get("/v1/status").json()
    assert status["version"] == test_settings.ga_version or status.get("version")
    assert "components" in status

    # ensure no open findings for readiness
    pack = compliance_pack(db)
    for f in pack["pentest"]["findings"]:
        if f["status"] == "open":
            close_pentest_finding(db, UUID(f["id"]), status="remediated")

    ready = client.get("/v1/ga/readiness", headers=auth_headers).json()
    assert ready["ga_version"]
    assert "eval_gates_green" in ready
    assert "ready" in ready


def test_ml_api_endpoints(client, auth_headers, db, seeded_db):
    evals = client.post("/v1/ml/evals/run", headers=auth_headers)
    assert evals.status_code == 200, evals.text
    assert any(r["passed"] for r in evals.json())

    forecast = client.get("/v1/ml/forecast", headers=auth_headers)
    assert forecast.status_code == 200
    assert "forecast" in forecast.json()

    project = Project(name="GA Pilot", description="phase8", tenant_id="default")
    db.add(project)
    db.commit()
    db.refresh(project)
    delay = client.get(f"/v1/ml/project-delay/{project.id}", headers=auth_headers)
    assert delay.status_code == 200, delay.text
    assert "probability" in delay.json()

    fb = client.post(
        "/v1/experts/feedback",
        headers=auth_headers,
        json={"person_key": "carol", "label": 1, "topic": "ops"},
    )
    assert fb.status_code == 200, fb.text


def test_employee_forbidden_on_admin_ga_routes(client, user_headers):
    assert client.get("/v1/ga/readiness", headers=user_headers).status_code == 403
    assert client.get("/v1/compliance/pack", headers=user_headers).status_code == 403
    assert client.post("/v1/evals/run", headers=user_headers, json={}).status_code == 403
