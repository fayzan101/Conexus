from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.config import Settings
from app.db.models import Document, Prediction, Project, ProjectMembership, Role, User
from app.deps import hash_password
from app.services.abac import evaluate_document_access
from app.services.agents import run_agent
from app.services.backup import backup_command_matrix
from app.services.compliance import compliance_pack, hardening_gates
from app.services.graph import GraphStore
from app.services.observability import record_request, render_prometheus, reset_metrics
from app.services.operating_system import predict_project_delay


def test_abac_empty_project_denies_unless_open(db, test_settings):
    user = User(
        email="u@example.com",
        hashed_password=hash_password("x"),
        role=Role.employee,
        tenant_id="default",
        clearance="internal",
        is_active=True,
    )
    project = Project(name="EmptyProj", tenant_id="default")
    db.add_all([user, project])
    db.commit()
    db.refresh(user)
    db.refresh(project)
    doc = Document(
        title="d",
        filename="d.txt",
        object_key="d",
        tenant_id="default",
        project_id=project.id,
        visibility="org",
        classification="internal",
        text_preview="x",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    closed = test_settings.model_copy(update={"project_open_if_empty": False})
    deny = evaluate_document_access(
        db, user=user, user_id=user.id, tenant_id="default", document=doc, settings=closed
    )
    assert deny.allowed is False

    opened = test_settings.model_copy(update={"project_open_if_empty": True})
    allow = evaluate_document_access(
        db, user=user, user_id=user.id, tenant_id="default", document=doc, settings=opened
    )
    assert allow.allowed is True


def test_prediction_tenant_scoped(db, seeded_db, test_settings):
    project = Project(name="P1", tenant_id="tenant-a")
    db.add(project)
    db.commit()
    db.refresh(project)
    pred = predict_project_delay(db, project, tenant_id="tenant-a")
    assert pred.tenant_id == "tenant-a"
    foreign = db.query(Prediction).filter(Prediction.tenant_id == "other").count()
    assert foreign == 0
    assert db.query(Prediction).filter(Prediction.tenant_id == "tenant-a").count() >= 1


def test_graph_search_requires_tenant_param():
    store = GraphStore.__new__(GraphStore)
    store.default_tenant = "t1"
    session = MagicMock()
    driver = MagicMock()
    driver.session.return_value.__enter__.return_value = session
    driver.session.return_value.__exit__.return_value = False
    store.driver = driver
    session.run.return_value = []
    store.search("Document", "rfc", tenant_id="t1")
    assert session.run.call_args.kwargs.get("tenant_id") == "t1" or "tenant_id" in str(
        session.run.call_args
    )


def test_agent_search_uses_acl_and_tenant(db, test_settings):
    user = User(
        email="agent@example.com",
        hashed_password=hash_password("x"),
        role=Role.employee,
        tenant_id="default",
        clearance="internal",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    class FakeStore:
        def search(self, *, vector, limit=10, project_id=None, tenant_id=None):
            assert tenant_id == "default"
            return []

    from app.services import agents as agents_mod
    from app.services import rag as rag_mod

    original = rag_mod.VectorStore
    rag_mod.VectorStore = lambda settings: FakeStore()  # type: ignore
    try:
        run = run_agent(
            db,
            test_settings,
            problem="What is Phoenix?",
            tenant_id="default",
            user_id=user.id,
            requested_tools=["search", "list_predictions"],
        )
        assert run.status == "completed"
        search_step = next(s for s in (run.tools_used or []) if s.get("tool") == "search")
        assert "hits" in search_step
    finally:
        rag_mod.VectorStore = original


def test_prometheus_render_and_compliance_honesty(db, test_settings):
    reset_metrics()
    record_request("GET", "/v1/search", 200, 12.0)
    text = render_prometheus()
    assert "eb_http_requests_total" in text

    pack = compliance_pack(db, test_settings)
    assert all(c["status"] == "partial" for c in pack["soc2_controls"])
    gates = hardening_gates(test_settings)
    assert gates["trust_hardening_complete"] is True

    cmds = backup_command_matrix(test_settings)
    assert "postgres" in cmds and cmds["postgres"]


def test_prod_forces_redis_queue():
    s = Settings(
        environment="staging",
        secret_key="prod-secret-not-demo",
        require_tls=True,
        auth_provider="oidc",
        auth_issuer="https://idp.example",
        auth_audience="eb",
        embedding_provider="openai",
        llm_api_key="sk-test",
        queue_backend="memory",
        queue_inline=True,
    )
    assert s.queue_backend == "redis"
    assert s.queue_inline is False
