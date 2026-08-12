"""Validate Phase 7 packaging files without helm/terraform CLIs."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_helm_chart_and_values_present():
    chart = (ROOT / "deploy/helm/enterprise-brain/Chart.yaml").read_text(encoding="utf-8")
    values = (ROOT / "deploy/helm/enterprise-brain/values.yaml").read_text(encoding="utf-8")
    assert "name: enterprise-brain" in chart
    assert "replicaCount:" in values
    assert "hpa:" in values
    assert "pdb:" in values
    assert "resources:" in values
    for name in (
        "api-deployment.yaml",
        "worker-deployment.yaml",
        "web-deployment.yaml",
        "hpa.yaml",
        "pdb.yaml",
        "ingress.yaml",
        "service.yaml",
    ):
        assert (ROOT / "deploy/helm/enterprise-brain/templates" / name).exists()


def test_env_values_files_exist():
    for env in ("dev", "staging", "prod"):
        text = (ROOT / f"deploy/helm/enterprise-brain/values-{env}.yaml").read_text(encoding="utf-8")
        assert f"environment: {env}" in text


def test_grafana_dashboard_and_alerts():
    dash = json.loads((ROOT / "deploy/observability/grafana-dashboard.json").read_text(encoding="utf-8"))
    titles = {p["title"] for p in dash["panels"]}
    assert "Search P95" in titles
    alerts = (ROOT / "deploy/observability/prometheus-alerts.yaml").read_text(encoding="utf-8")
    assert "enterprise-brain-slo" in alerts
    assert "eb_search_duration_ms_p95" in alerts


def test_terraform_env_tfvars():
    for env in ("dev", "staging", "prod"):
        text = (ROOT / f"deploy/terraform/environments/{env}.tfvars").read_text(encoding="utf-8")
        assert f'environment     = "{env}"' in text
        assert "namespace" in text
