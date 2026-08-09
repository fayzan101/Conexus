from app.config import Settings
from app.connectors.drive import google_oauth_authorize_url
from app.connectors.jira import jira_oauth_authorize_url
from app.connectors.teams import TeamsConnector, ms_oauth_authorize_url
from app.connectors.email import OutlookConnector, GmailConnector
from app.connectors.jira import JiraConnector
from app.db.models import Document, User, Role
from app.deps import create_access_token, hash_password
from app.services.entity_resolution import merge_entities, upsert_entity
from app.services.events import MemoryEventBus, get_event_bus, reset_event_bus
from app.services.hybrid_search import hybrid_search, keyword_search
from app.services.rag import filter_hits_by_acl


def test_remaining_connectors_fixture_and_oauth_urls():
    teams = TeamsConnector()
    teams.authenticate({"access_token": "t", "messages": [{"id": "1", "text": "hello", "createdDateTime": "2026-01-01T00:00:00Z"}]})
    assert teams.sync().stats["mode"] == "fixture"

    jira = JiraConnector()
    jira.authenticate({"access_token": "t", "issues": [{"key": "EB-9", "fields": {"summary": "Scale"}}]})
    assert jira.sync().stats["mode"] == "fixture"

    outlook = OutlookConnector()
    outlook.authenticate({"access_token": "t", "messages": [{"id": "m1", "subject": "Hi", "body": "body"}]})
    assert outlook.sync().stats["mode"] == "fixture"

    gmail = GmailConnector()
    gmail.authenticate({"access_token": "t", "messages": [{"id": "g1", "subject": "G", "snippet": "s"}]})
    assert gmail.sync().stats["mode"] == "fixture"

    settings = Settings(
        environment="test",
        auth_provider="dev",
        ms_client_id="ms",
        google_client_id="g",
        jira_client_id="j",
        api_base_url="http://localhost:8000",
    )
    assert "microsoftonline.com" in ms_oauth_authorize_url(settings, state="s", scopes="User.Read")
    assert "accounts.google.com" in google_oauth_authorize_url(settings, state="s", scopes="drive")
    assert "auth.atlassian.com" in jira_oauth_authorize_url(settings, state="s")


def test_event_bus_backpressure():
    reset_event_bus()
    bus = MemoryEventBus(max_depth=2)
    bus.publish("t", {"a": 1})
    bus.publish("t", {"a": 2})
    bus.publish("t", {"a": 3})  # dropped
    assert bus.depth() == 2


def test_entity_merge_and_tenant_isolation(db, test_settings):
    a = upsert_entity(db, tenant_id="t1", entity_type="person", display_name="Ada Lovelace", aliases=["Ada"])
    b = upsert_entity(db, tenant_id="t1", entity_type="person", display_name="Ada L", aliases=["Ada Lovelace"])
    # Force duplicate-ish merge
    merged = merge_entities(
        db, tenant_id="t1", source_id=b.id, target_id=a.id, reason="same person", user_id=None
    )
    assert "Ada L" in (merged.aliases or []) or "Ada Lovelace" in (merged.aliases or [])

    try:
        merge_entities(db, tenant_id="t2", source_id=a.id, target_id=a.id, reason="x", user_id=None)
        assert False
    except ValueError:
        pass


def test_tenant_vector_acl_no_leak(db, test_settings):
    u1 = User(
        email="a@t1.example",
        hashed_password=hash_password("x"),
        role=Role.employee,
        tenant_id="tenant-a",
        is_active=True,
    )
    u2 = User(
        email="b@t2.example",
        hashed_password=hash_password("x"),
        role=Role.employee,
        tenant_id="tenant-b",
        is_active=True,
    )
    db.add_all([u1, u2])
    db.commit()
    db.refresh(u1)
    db.refresh(u2)

    doc_b = Document(
        tenant_id="tenant-b",
        title="Secret B",
        filename="b.txt",
        object_key="b",
        text_preview="tenant b only",
        visibility="org",
    )
    db.add(doc_b)
    db.commit()
    db.refresh(doc_b)

    hits = [
        {
            "id": "1",
            "score": 0.9,
            "payload": {
                "document_id": str(doc_b.id),
                "title": "Secret B",
                "snippet": "tenant b only",
                "visibility": "org",
                "tenant_id": "tenant-b",
            },
        }
    ]
    allowed = filter_hits_by_acl(db, hits, user_id=u1.id, tenant_id="tenant-a")
    assert allowed == []


def test_hybrid_keyword_tenant_scoped(db, test_settings):
    db.add(
        Document(
            tenant_id="default",
            title="Phoenix plan",
            filename="p.txt",
            object_key="p",
            text_preview="Project Phoenix scale plan",
            visibility="org",
        )
    )
    db.add(
        Document(
            tenant_id="other",
            title="Phoenix plan",
            filename="o.txt",
            object_key="o",
            text_preview="should not appear",
            visibility="org",
        )
    )
    db.commit()
    hits = keyword_search(db, query="Phoenix", tenant_id="default", limit=10)
    assert len(hits) >= 1
    assert all(h["payload"]["tenant_id"] == "default" for h in hits)


def test_knowledge_apis(client, auth_headers):
    created = client.post(
        "/v1/knowledge/entities",
        headers=auth_headers,
        json={"entity_type": "project", "display_name": "Phoenix", "aliases": ["Project Phoenix"]},
    )
    assert created.status_code == 200, created.text
    dups = client.get("/v1/knowledge/entities/duplicates", headers=auth_headers, params={"entity_type": "project"})
    assert dups.status_code == 200
    metrics = client.get("/v1/knowledge/events/metrics", headers=auth_headers)
    assert metrics.status_code == 200
    assert "published" in metrics.json()


def test_oauth_start_for_new_providers(client, auth_headers, test_settings, monkeypatch):
    # Without client ids -> 400
    res = client.get("/v1/connectors/teams/oauth/start", headers=auth_headers)
    assert res.status_code == 400

    # Inject settings via dependency override already; mutate fixture settings
    test_settings.ms_client_id = "ms-id"
    test_settings.google_client_id = "g-id"
    test_settings.jira_client_id = "j-id"
    ok = client.get("/v1/connectors/teams/oauth/start", headers=auth_headers)
    assert ok.status_code == 200
    assert "authorize_url" in ok.json()
