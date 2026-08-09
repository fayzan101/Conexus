from uuid import uuid4

from app.db.models import Document
from app.services.rag import filter_hits_by_acl, grounded_answer, hits_to_search_results


class FakeVectorStore:
    def __init__(self, hits):
        self.hits = hits

    def search(self, *, vector, limit=10, project_id=None, tenant_id=None):
        return self.hits[:limit]


def test_filter_hits_by_acl_excludes_private(db, seeded_db, test_settings):
    owner = seeded_db.query(Document).first()
    # create private doc owned by admin
    from app.db.models import User

    admin = seeded_db.query(User).filter_by(email=test_settings.dev_admin_email).one()
    employee = seeded_db.query(User).filter_by(email=test_settings.dev_user_email).one()

    private = Document(
        id=uuid4(),
        title="Secret",
        filename="secret.txt",
        content_type="text/plain",
        object_key="local/secret",
        uploaded_by=admin.id,
        visibility="private",
        text_preview="secret",
    )
    seeded_db.add(private)
    seeded_db.commit()

    hits = [
        {
            "id": "1",
            "score": 0.9,
            "payload": {
                "visibility": "private",
                "document_id": str(private.id),
                "snippet": "secret",
                "title": "Secret",
            },
        },
        {
            "id": "2",
            "score": 0.8,
            "payload": {
                "visibility": "org",
                "document_id": str(uuid4()),
                "snippet": "public",
                "title": "Public",
            },
        },
    ]
    allowed = filter_hits_by_acl(seeded_db, hits, user_id=employee.id)
    assert len(allowed) == 1
    assert allowed[0]["id"] == "2"

    allowed_owner = filter_hits_by_acl(seeded_db, hits, user_id=admin.id)
    assert len(allowed_owner) == 2


def test_grounded_answer_refuses_without_evidence(db, seeded_db, test_settings):
    from app.db.models import User

    user = seeded_db.query(User).filter_by(email=test_settings.dev_user_email).one()
    answer = grounded_answer(
        seeded_db,
        test_settings,
        query="unknown topic",
        user_id=user.id,
        vector_store=FakeVectorStore([]),
    )
    assert answer["confidence"] < 0.3
    assert answer["sources"] == []
    assert "could not find accessible evidence" in answer["content"].lower()


def test_grounded_answer_with_stub_llm(db, seeded_db, test_settings):
    from app.db.models import User

    user = seeded_db.query(User).filter_by(email=test_settings.dev_user_email).one()
    hits = [
        {
            "id": "h1",
            "score": 0.88,
            "payload": {
                "visibility": "org",
                "document_id": str(uuid4()),
                "snippet": "Kubernetes was approved for Project Phoenix.",
                "title": "RFC",
                "type": "document",
            },
        }
    ]

    def fake_llm(settings, *, query, evidence):
        return f"LLM says: {evidence[0]['snippet']}"

    answer = grounded_answer(
        seeded_db,
        test_settings,
        query="Why Kubernetes?",
        user_id=user.id,
        vector_store=FakeVectorStore(hits),
        llm_fn=fake_llm,
    )
    assert answer["sources"]
    assert answer["content"].startswith("LLM says:")
    assert answer["confidence"] >= 0.35


def test_hits_to_search_results():
    out = hits_to_search_results(
        [{"id": "a", "score": 1.0, "payload": {"snippet": "x", "title": "T", "type": "document"}}]
    )
    assert out[0]["snippet"] == "x"
    assert out[0]["source"]["title"] == "T"
