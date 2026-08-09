from datetime import datetime, timezone

from app.db.models import Document
from app.services.intelligence import rank_experts, record_expertise_from_text, score_document_freshness
from app.services.hybrid_search import hybrid_search, keyword_search


def test_score_document_freshness():
    doc = Document(
        title="Old",
        filename="a.txt",
        content_type="text/plain",
        object_key="x",
        text_preview="hello world",
        source_system="upload",
    )
    doc.created_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
    scores = score_document_freshness(doc, now=datetime(2026, 1, 1, tzinfo=timezone.utc))
    assert scores["freshness"] < 0.5
    assert scores["suggested_update"]


def test_rank_experts(db, seeded_db):
    record_expertise_from_text(
        seeded_db,
        person_key="Alice Smith",
        text="Project Phoenix architecture",
        source_system="github",
        weight=2.0,
    )
    record_expertise_from_text(
        seeded_db,
        person_key="Bob Jones",
        text="Project Phoenix docs",
        source_system="meeting",
        weight=1.0,
    )
    ranked = rank_experts(seeded_db, topic="Phoenix")
    assert ranked[0]["person"] == "Alice Smith"
    assert ranked[0]["score"] >= ranked[1]["score"]


def test_keyword_and_hybrid_search(db, seeded_db, test_settings):
    from app.db.models import User

    user = seeded_db.query(User).filter_by(email=test_settings.dev_user_email).one()
    doc = Document(
        title="Kubernetes Decision",
        filename="k8s.txt",
        content_type="text/plain",
        object_key="local/k8s",
        text_preview="We adopted Kubernetes for Project Phoenix.",
        source_system="upload",
        visibility="org",
    )
    seeded_db.add(doc)
    seeded_db.commit()

    kw = keyword_search(seeded_db, query="Kubernetes")
    assert kw

    class FakeVector:
        def search(self, *, vector, limit=10, project_id=None, tenant_id=None):
            return []

    results = hybrid_search(
        seeded_db,
        test_settings,
        query="Kubernetes",
        user_id=user.id,
        vector_store=FakeVector(),
    )
    assert results
    assert any("Kubernetes" in (r.get("snippet") or "") or "Kubernetes" in str(r["source"].get("title")) for r in results)
