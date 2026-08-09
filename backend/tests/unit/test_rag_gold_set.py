"""RAG gold-set eval (N>=50): recall@5 + citation presence gates."""

from __future__ import annotations

from app.db.models import Role, User
from app.deps import hash_password
from app.services.embeddings import HashEmbedder
from app.services.llm import check_faithfulness, stub_synthesize
from app.services.rag import filter_hits_by_acl, grounded_answer


class FakeVectorStore:
    def __init__(self, corpus: list[dict], dim: int = 384):
        self.corpus = corpus
        self.dim = dim

    def search(self, *, vector, limit=10, project_id=None, tenant_id=None):
        scored = []
        for item in self.corpus:
            if project_id and item["payload"].get("project_id") != str(project_id):
                continue
            if tenant_id and item["payload"].get("tenant_id") and item["payload"].get("tenant_id") != tenant_id:
                continue
            score = sum(x * y for x, y in zip(vector, item["vector"]))
            scored.append({"id": item["id"], "score": score, "payload": item["payload"]})
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:limit]


def _build_gold_corpus(dim: int = 384, n_docs: int = 20) -> tuple[list[dict], list[dict]]:
    embedder = HashEmbedder(dim=dim)
    topics = [
        ("Phoenix", "Project Phoenix migration timeline and Neo4j decision"),
        ("ACL", "Private document ACL filtering for search results"),
        ("Slack", "Slack connector OAuth and webhook signature verification"),
        ("Ingest", "Redis ingest queue dead letter and retry jobs"),
        ("Executive", "Executive dashboard KPI risk and opportunity signals"),
    ]
    corpus = []
    gold = []
    for i in range(n_docs):
        topic_name, topic_text = topics[i % len(topics)]
        text = f"{topic_text}. Document {i}. Keywords: {topic_name} enterprise brain pilot."
        vec = embedder.embed([text])[0]
        doc_id = f"doc-{i}"
        corpus.append(
            {
                "id": f"chunk-{i}",
                "vector": vec,
                "payload": {
                    "document_id": doc_id,
                    "title": f"{topic_name} note {i}",
                    "snippet": text,
                    "visibility": "org",
                    "type": "document",
                },
            }
        )
        gold.append(
            {
                "query": f"What do we know about {topic_name} document {i}?",
                "relevant_ids": {doc_id},
                "must_cite": True,
            }
        )

    while len(gold) < 50:
        idx = len(gold) % n_docs
        topic_name, _ = topics[idx % len(topics)]
        gold.append(
            {
                "query": f"Summarize {topic_name} evidence from note {idx}",
                "relevant_ids": {f"doc-{idx}"},
                "must_cite": True,
            }
        )
    return corpus, gold


def test_rag_gold_set_recall_and_citations(db, test_settings):
    user = User(
        email="gold@example.com",
        full_name="Gold",
        hashed_password=hash_password("x"),
        role=Role.employee,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    dim = test_settings.embedding_dim
    corpus, gold = _build_gold_corpus(dim=dim)
    store = FakeVectorStore(corpus, dim=dim)
    embedder = HashEmbedder(dim=dim)

    hits_at_5 = 0
    cited = 0
    for item in gold:
        qvec = embedder.embed([item["query"]])[0]
        raw = store.search(vector=qvec, limit=5)
        allowed = filter_hits_by_acl(db, raw, user_id=user.id)
        retrieved_docs = {(h.get("payload") or {}).get("document_id") for h in allowed}
        if item["relevant_ids"] & retrieved_docs:
            hits_at_5 += 1

        answer = grounded_answer(
            db,
            test_settings,
            query=item["query"],
            user_id=user.id,
            vector_store=store,
            llm_fn=lambda settings, query, evidence: stub_synthesize(
                query=query, hits=[{"snippet": e.get("snippet")} for e in evidence]
            ),
        )
        if answer["sources"] and check_faithfulness(answer["content"], len(answer["sources"]))["ok"]:
            cited += 1

    n = len(gold)
    recall = hits_at_5 / n
    citation_rate = cited / n
    assert n >= 50
    assert recall >= 0.30, f"recall@5={recall:.2f} below gate"
    assert citation_rate >= 0.90, f"citation_rate={citation_rate:.2f} below gate"
