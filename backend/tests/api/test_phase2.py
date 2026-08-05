from datetime import datetime, timezone


def test_connectors_list_and_sync(client, auth_headers):
    listed = client.get("/v1/connectors", headers=auth_headers)
    assert listed.status_code == 200
    assert "slack" in listed.json()["providers"]

    connected = client.post(
        "/v1/connectors/slack/connect",
        headers=auth_headers,
        json={
            "display_name": "Pilot Slack",
            "credentials": {
                "access_token": "xoxb-test",
                "messages": [
                    {
                        "ts": "1710000000.1",
                        "channel": "eng",
                        "text": "Decision: use Neo4j for Project Phoenix",
                        "user": "U1",
                    }
                ],
            },
        },
    )
    assert connected.status_code == 201, connected.text
    account_id = connected.json()["id"]

    synced = client.post(f"/v1/connectors/accounts/{account_id}/sync", headers=auth_headers)
    assert synced.status_code == 200, synced.text
    assert synced.json()["stored"] == 1


def test_timeline_and_decision_links(client, auth_headers):
    event = client.post(
        "/v1/timeline",
        headers=auth_headers,
        json={
            "event_type": "release",
            "title": "v0.1 shipped",
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "summary": "Phase 1 complete",
        },
    )
    assert event.status_code == 201, event.text

    timeline = client.get("/v1/timeline", headers=auth_headers)
    assert timeline.status_code == 200
    assert len(timeline.json()) >= 1

    decision = client.post(
        "/v1/decisions",
        headers=auth_headers,
        json={
            "title": "Adopt Neo4j",
            "context": "Graph memory for Project Phoenix",
            "status": "approved",
            "links": [
                {
                    "link_type": "document",
                    "target_id": "doc-1",
                    "target_title": "RFC",
                    "source_system": "upload",
                }
            ],
        },
    )
    assert decision.status_code == 201, decision.text
    did = decision.json()["id"]
    links = client.get(f"/v1/decisions/{did}/links", headers=auth_headers)
    assert links.status_code == 200
    assert len(links.json()) == 1

    who = client.get("/v1/decisions/query/who-approved", headers=auth_headers, params={"q": "Neo4j"})
    assert who.status_code == 200
    assert any(row["title"] == "Adopt Neo4j" for row in who.json())


def test_freshness_and_expertise_endpoints(client, auth_headers):
    refresh = client.post("/v1/freshness/refresh", headers=auth_headers)
    assert refresh.status_code == 200
    experts = client.get("/v1/expertise", headers=auth_headers)
    assert experts.status_code == 200
    assert "experts" in experts.json()
