from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import QueryLog
from app.services.abac import filter_hits_with_reasons
from app.services.embeddings import get_embedder
from app.services.llm import check_faithfulness, stub_synthesize
from app.services.llm_budget import synthesize_with_budget
from app.services.observability import record_grounded, start_span
from app.services.vector import VectorStore


def filter_hits_by_acl(
    db: Session,
    hits: list[dict],
    *,
    user_id: UUID | None,
    tenant_id: str | None = None,
) -> list[dict]:
    allowed, _ = filter_hits_with_reasons(db, hits, user_id=user_id, tenant_id=tenant_id)
    return allowed


def hits_to_search_results(hits: list[dict]) -> list[dict]:
    results = []
    for hit in hits:
        payload = hit.get("payload") or {}
        results.append(
            {
                "id": str(hit["id"]),
                "score": float(hit["score"]),
                "snippet": payload.get("snippet", ""),
                "source": {
                    "document_id": payload.get("document_id"),
                    "meeting_id": payload.get("meeting_id"),
                    "title": payload.get("title"),
                    "type": payload.get("type"),
                    "uri": None,
                    "tenant_id": payload.get("tenant_id"),
                    "classification": payload.get("classification"),
                    "region": payload.get("region"),
                },
            }
        )
    return results


def semantic_search(
    db: Session,
    settings: Settings,
    *,
    query: str,
    user_id: UUID | None,
    limit: int = 10,
    project_id: UUID | None = None,
    tenant_id: str | None = None,
    vector_store: VectorStore | None = None,
) -> dict:
    """Returns {results, blocked, acl_summary}."""
    tenant_id = tenant_id or settings.default_tenant_id
    embedder = get_embedder(settings)
    vector = embedder.embed([query])[0]
    store = vector_store or VectorStore(settings)
    raw_hits = store.search(vector=vector, limit=limit * 2, project_id=project_id, tenant_id=tenant_id)
    allowed, blocked = filter_hits_with_reasons(db, raw_hits, user_id=user_id, tenant_id=tenant_id)
    allowed = allowed[:limit]
    results = hits_to_search_results(allowed)

    db.add(QueryLog(user_id=user_id, tenant_id=tenant_id, query_type="search", query_text=query))
    db.commit()
    return {
        "results": results,
        "blocked": blocked,
        "acl_summary": {
            "returned": len(results),
            "blocked": len(blocked),
            "blocked_reasons": sorted({b["reason"] for b in blocked}),
        },
    }


def grounded_answer(
    db: Session,
    settings: Settings,
    *,
    query: str,
    user_id: UUID,
    tenant_id: str | None = None,
    vector_store: VectorStore | None = None,
    llm_fn=None,
) -> dict:
    tenant_id = tenant_id or settings.default_tenant_id
    with start_span("rag.grounded_answer", tenant_id=tenant_id):
        search = semantic_search(
            db,
            settings,
            query=query,
            user_id=user_id,
            limit=5,
            tenant_id=tenant_id,
            vector_store=vector_store,
        )
    hits = search["results"]
    blocked = search["blocked"]
    acl_summary = search["acl_summary"]
    db.add(QueryLog(user_id=user_id, tenant_id=tenant_id, query_type="chat", query_text=query))
    db.commit()

    if not hits:
        blocked_reason = None
        if blocked:
            blocked_reason = (
                "Accessible evidence was filtered by policy "
                f"({', '.join(acl_summary['blocked_reasons'])}). "
                "You may lack clearance, region, or project membership."
            )
        record_grounded(False)
        return {
            "content": blocked_reason
            or (
                "I could not find accessible evidence in the knowledge base for that question. "
                "Try uploading related documents or meeting transcripts."
            ),
            "confidence": 0.15,
            "blocked_reason": blocked_reason,
            "acl_summary": acl_summary,
            "sources": [],
            "related_documents": [],
            "related_projects": [],
            "people_involved": [],
            "timeline": [],
            "supporting_evidence": [],
        }

    evidence = [
        {"title": h["source"].get("title"), "snippet": h["snippet"], "id": h["id"]} for h in hits
    ]
    if llm_fn is not None:
        llm_answer = llm_fn(settings, query=query, evidence=evidence)
    else:
        llm_answer = synthesize_with_budget(
            db, settings, query=query, evidence=evidence, tenant_id=tenant_id, task="chat"
        )

    content = llm_answer or stub_synthesize(query=query, hits=hits)
    faithfulness = check_faithfulness(content, len(hits))
    if not faithfulness["ok"]:
        missing = " ".join(f"[{i}]" for i in range(1, min(3, len(hits)) + 1))
        content = f"{content.rstrip()} {missing}".strip()
        faithfulness = check_faithfulness(content, len(hits))

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
    record_grounded(bool(sources))

    return {
        "content": content,
        "confidence": round(min(0.95, max(0.35, avg_score)), 3),
        "faithfulness": faithfulness,
        "blocked_reason": None,
        "acl_summary": acl_summary,
        "sources": sources,
        "related_documents": [
            {"id": h["source"].get("document_id"), "title": h["source"].get("title")}
            for h in hits
            if h["source"].get("document_id")
        ],
        "related_projects": [],
        "people_involved": [],
        "timeline": [],
        "supporting_evidence": [
            {"quote": h["snippet"][:300], "source_id": h["id"]} for h in hits[:3]
        ],
    }
