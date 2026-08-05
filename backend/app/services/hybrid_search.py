from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import Document, DocumentChunk, QueryLog
from app.services.rag import filter_hits_by_acl, hits_to_search_results, semantic_search
from app.services.vector import VectorStore


def keyword_search(
    db: Session,
    *,
    query: str,
    limit: int = 20,
    project_id: UUID | None = None,
    source_system: str | None = None,
) -> list[dict]:
    q = db.query(Document)
    if project_id:
        q = q.filter(Document.project_id == project_id)
    if source_system:
        q = q.filter(Document.source_system == source_system)
    like = f"%{query}%"
    docs = (
        q.filter(or_(Document.title.ilike(like), Document.text_preview.ilike(like)))
        .order_by(Document.created_at.desc())
        .limit(limit)
        .all()
    )
    hits = []
    for doc in docs:
        snippet = (doc.text_preview or "")[:400]
        score = 0.55
        title_l = (doc.title or "").lower()
        if query.lower() in title_l:
            score += 0.25
        hits.append(
            {
                "id": f"kw-{doc.id}",
                "score": score,
                "payload": {
                    "document_id": str(doc.id),
                    "title": doc.title,
                    "snippet": snippet,
                    "type": "document",
                    "visibility": doc.visibility,
                    "source_system": doc.source_system,
                },
            }
        )
    return hits


def hybrid_search(
    db: Session,
    settings: Settings,
    *,
    query: str,
    user_id: UUID | None,
    limit: int = 10,
    project_id: UUID | None = None,
    source_system: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    types: list[str] | None = None,
    people: list[str] | None = None,
    vector_store: VectorStore | None = None,
) -> list[dict]:
    vector_hits = semantic_search(
        db,
        settings,
        query=query,
        user_id=user_id,
        limit=limit,
        project_id=project_id,
        vector_store=vector_store,
    )
    # semantic_search already returns formatted results + logs; convert back-ish via keyword path
    kw_raw = keyword_search(
        db, query=query, limit=limit * 2, project_id=project_id, source_system=source_system
    )
    kw_allowed = filter_hits_by_acl(db, kw_raw, user_id=user_id)
    kw_results = hits_to_search_results(kw_allowed)

    merged: dict[str, dict] = {}
    for hit in vector_hits:
        key = hit["source"].get("document_id") or hit["id"]
        item = dict(hit)
        item["score"] = float(hit["score"]) * 0.7
        item["source"] = {**hit["source"], "retrieval": "vector"}
        merged[str(key)] = item

    for hit in kw_results:
        key = hit["source"].get("document_id") or hit["id"]
        key = str(key)
        if key in merged:
            merged[key]["score"] = min(0.99, merged[key]["score"] + float(hit["score"]) * 0.45)
            merged[key]["source"]["retrieval"] = "hybrid"
        else:
            item = dict(hit)
            item["score"] = float(hit["score"]) * 0.55
            item["source"] = {**hit["source"], "retrieval": "keyword"}
            merged[key] = item

    results = list(merged.values())

    def _pass_filters(hit: dict) -> bool:
        src = hit.get("source") or {}
        if types and src.get("type") and src.get("type") not in types:
            return False
        if source_system and src.get("source_system") and src.get("source_system") != source_system:
            # vector hits may not include source_system; allow through if missing
            pass
        if people:
            snippet = (hit.get("snippet") or "").lower()
            if not any(p.lower() in snippet for p in people):
                return False
        return True

    results = [r for r in results if _pass_filters(r)]
    results.sort(key=lambda r: r["score"], reverse=True)
    results = results[:limit]

    db.add(QueryLog(user_id=user_id, query_type="hybrid_search", query_text=query))
    db.commit()
    return results


def project_memory(db: Session, project_id: UUID) -> dict:
    docs = db.query(Document).filter(Document.project_id == project_id).all()
    chunks = 0
    for d in docs:
        chunks += db.query(DocumentChunk).filter(DocumentChunk.document_id == d.id).count()
    return {
        "project_id": str(project_id),
        "documents": [{"id": str(d.id), "title": d.title, "source_system": d.source_system} for d in docs],
        "document_count": len(docs),
        "chunk_count": chunks,
    }
