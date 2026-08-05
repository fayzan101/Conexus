from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import Document, QueryLog
from app.services.embeddings import get_embedder
from app.services.vector import VectorStore


def semantic_search(
    db: Session,
    settings: Settings,
    *,
    query: str,
    user_id: UUID | None,
    limit: int = 10,
    project_id: UUID | None = None,
) -> list[dict]:
    embedder = get_embedder(settings)
    vector = embedder.embed([query])[0]
    store = VectorStore(settings)
    hits = store.search(vector=vector, limit=limit, project_id=project_id)

    results = []
    for hit in hits:
        payload = hit["payload"]
        # ACL: MVP allows org-visible; private only if uploader matches (future)
        visibility = payload.get("visibility", "org")
        if visibility == "private":
            doc_id = payload.get("document_id")
            if doc_id:
                doc = db.get(Document, UUID(doc_id))
                if doc and doc.uploaded_by and user_id and doc.uploaded_by != user_id:
                    continue
        results.append(
            {
                "id": hit["id"],
                "score": hit["score"],
                "snippet": payload.get("snippet", ""),
                "source": {
                    "document_id": payload.get("document_id"),
                    "meeting_id": payload.get("meeting_id"),
                    "title": payload.get("title"),
                    "type": payload.get("type"),
                    "uri": None,
                },
            }
        )

    db.add(
        QueryLog(
            user_id=user_id,
            query_type="search",
            query_text=query,
        )
    )
    db.commit()
    return results


def grounded_answer(
    db: Session,
    settings: Settings,
    *,
    query: str,
    user_id: UUID,
) -> dict:
    hits = semantic_search(db, settings, query=query, user_id=user_id, limit=5)
    db.add(QueryLog(user_id=user_id, query_type="chat", query_text=query))
    db.commit()

    if not hits:
        return {
            "content": (
                "I could not find accessible evidence in the knowledge base for that question. "
                "Try uploading related documents or meeting transcripts."
            ),
            "confidence": 0.15,
            "sources": [],
            "related_documents": [],
            "related_projects": [],
            "people_involved": [],
            "timeline": [],
            "supporting_evidence": [],
        }

    # Stub synthesis (replace with LLM when LLM_API_KEY is set)
    if settings.llm_api_key:
        # Placeholder for real provider call; keep deterministic scaffold behavior.
        pass

    snippets = [h["snippet"] for h in hits if h["snippet"]]
    answer = (
        f"Based on {len(hits)} evidence source(s): "
        + " ".join(snippets[:2])
    )
    if len(answer) > 1200:
        answer = answer[:1200] + "…"

    sources = [
        {
            "id": h["id"],
            "title": h["source"].get("title"),
            "score": h["score"],
            "snippet": h["snippet"][:240],
            "type": h["source"].get("type"),
        }
        for h in hits
    ]
    avg_score = sum(h["score"] for h in hits) / len(hits)

    return {
        "content": answer,
        "confidence": round(min(0.95, max(0.35, avg_score)), 3),
        "sources": sources,
        "related_documents": [
            {"id": h["source"].get("document_id"), "title": h["source"].get("title")}
            for h in hits
            if h["source"].get("document_id")
        ],
        "related_projects": [],
        "people_involved": [],
        "timeline": [],
        "supporting_evidence": [{"quote": h["snippet"][:300], "source_id": h["id"]} for h in hits[:3]],
    }
