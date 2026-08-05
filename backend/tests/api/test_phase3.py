def test_phase3_os_apis(client, auth_headers):
    # dependencies
    dep = client.post(
        "/v1/dependencies",
        headers=auth_headers,
        json={
            "from_type": "service",
            "from_id": "billing-api",
            "to_type": "database",
            "to_id": "billing-db",
            "criticality": 0.85,
        },
    )
    assert dep.status_code == 201, dep.text

    impact = client.get("/v1/dependencies/impact/billing-api", headers=auth_headers)
    assert impact.status_code == 200
    assert "billing-db" in impact.json()["impacted_nodes"]

    # predictions + workflows
    preds = client.post("/v1/predictions/run", headers=auth_headers)
    assert preds.status_code == 200
    listed = client.get("/v1/predictions", headers=auth_headers)
    assert listed.status_code == 200

    workflows = client.post("/v1/workflows/detect", headers=auth_headers)
    assert workflows.status_code == 200

    opps = client.post("/v1/opportunities/discover", headers=auth_headers)
    assert opps.status_code == 200

    recs = client.post("/v1/recommendations/generate", headers=auth_headers)
    assert recs.status_code == 200

    research = client.post(
        "/v1/research/run",
        headers=auth_headers,
        json={"problem": "Why are projects delayed?"},
    )
    assert research.status_code == 200, research.text
    assert research.json()["executive_summary"]

    dash = client.get("/v1/executive/dashboard", headers=auth_headers)
    assert dash.status_code == 200
    body = dash.json()
    assert "knowledge_health" in body
    assert "high_risk_predictions" in body
