from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import or_, text
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
    tenant_id: str | None = None,
) -> list[dict]:
    """FTS on Postgres when available; ILIKE fallback (SQLite / missing FTS)."""
    dialect = db.bind.dialect.name if db.bind is not None else "sqlite"
    hits: list[dict] = []

    if dialect == "postgresql":
        try:
            sql = text(
                """
                SELECT id, title, text_preview, visibility, source_system, project_id,
                       ts_rank(
                         to_tsvector('english', coalesce(title,'') || ' ' || coalesce(text_preview,'')),
                         plainto_tsquery('english', :q)
                       ) AS rank
                FROM documents
                WHERE tenant_id = :tenant
                  AND to_tsvector('english', coalesce(title,'') || ' ' || coalesce(text_preview,''))
                      @@ plainto_tsquery('english', :q)
                ORDER BY rank DESC
                LIMIT :limit
                """
            )
            rows = db.execute(
                sql, {"q": query, "tenant": tenant_id or "default", "limit": limit}
            ).mappings().all()
            for row in rows:
                if project_id and row["project_id"] and str(row["project_id"]) != str(project_id):
                    continue
                if source_system and row["source_system"] != source_system:
                    continue
                hits.append(
                    {
                        "id": f"fts-{row['id']}",
                        "score": float(row["rank"] or 0.5) + 0.4,
                        "payload": {
                            "document_id": str(row["id"]),
                            "title": row["title"],
                            "snippet": (row["text_preview"] or "")[:400],
                            "type": "document",
                            "visibility": row["visibility"],
                            "source_system": row["source_system"],
                            "tenant_id": tenant_id,
                        },
                    }
                )
            if hits:
                return hits
        except Exception:
            pass

    q = db.query(Document)
    if tenant_id:
        q = q.filter(Document.tenant_id == tenant_id)
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
                    "tenant_id": doc.tenant_id,
                },
            }
        )
    return hits


def _lexical_rerank(query: str, results: list[dict]) -> list[dict]:
    q_tokens = {t for t in query.lower().split() if len(t) > 2}
    if not q_tokens:
        return results
    for hit in results:
        snippet = (hit.get("snippet") or "").lower()
        title = ((hit.get("source") or {}).get("title") or "").lower()
        blob = f"{title} {snippet}"
        overlap = sum(1 for t in q_tokens if t in blob)
        boost = min(0.25, overlap * 0.05)
        hit["score"] = min(0.99, float(hit["score"]) + boost)
        hit.setdefault("source", {})["rerank"] = "lexical"
    results.sort(key=lambda r: r["score"], reverse=True)
    return results


def _graph_expand(
    settings: Settings,
    *,
    seed_ids: list[str],
    tenant_id: str,
) -> list[dict]:
    if not seed_ids or settings.hybrid_graph_hops < 1:
        return []
    try:
        from app.services.graph import GraphStore

        graph = GraphStore(settings)
        expanded: list[dict] = []
        try:
            for sid in seed_ids[:5]:
                for hop in graph.neighbors(sid, limit=settings.hybrid_graph_limit):
                    props = hop.get("properties") or {}
                    if props.get("tenant_id") and props.get("tenant_id") != tenant_id:
                        continue
                    expanded.append(
                        {
                            "id": f"graph-{hop.get('id')}",
                            "score": 0.42,
                            "snippet": props.get("title") or props.get("name") or hop.get("label"),
                            "source": {
                                "document_id": props.get("id") if hop.get("label") == "Document" else None,
                                "title": props.get("title") or props.get("name"),
                                "type": (hop.get("label") or "node").lower(),
                                "retrieval": "graph",
                                "tenant_id": tenant_id,
                            },
                        }
                    )
        finally:
            graph.close()
        return expanded
    except Exception:
        return []


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
    tenant_id: str | None = None,
    vector_store: VectorStore | None = None,
) -> list[dict]:
    tenant_id = tenant_id or "default"
    vector_hits = semantic_search(
        db,
        settings,
        query=query,
        user_id=user_id,
        limit=limit,
        project_id=project_id,
        tenant_id=tenant_id,
        vector_store=vector_store,
    )
    kw_raw = keyword_search(
        db,
        query=query,
        limit=limit * 2,
        project_id=project_id,
        source_system=source_system,
        tenant_id=tenant_id,
    )
    kw_allowed = filter_hits_by_acl(db, kw_raw, user_id=user_id, tenant_id=tenant_id)
    kw_results = hits_to_search_results(kw_allowed)

    merged: dict[str, dict] = {}
    for hit in vector_hits:
        key = hit["source"].get("document_id") or hit["id"]
        item = dict(hit)
        item["score"] = float(hit["score"]) * 0.7
        item["source"] = {**hit["source"], "retrieval": "vector"}
        merged[str(key)] = item

    for hit in kw_results:
        key = str(hit["source"].get("document_id") or hit["id"])
        if key in merged:
            merged[key]["score"] = min(0.99, merged[key]["score"] + float(hit["score"]) * 0.45)
            merged[key]["source"]["retrieval"] = "hybrid"
        else:
            item = dict(hit)
            item["score"] = float(hit["score"]) * 0.55
            item["source"] = {**hit["source"], "retrieval": "keyword"}
            merged[key] = item

    seed_ids = [str(v["source"].get("document_id")) for v in merged.values() if v["source"].get("document_id")]
    for ghit in _graph_expand(settings, seed_ids=seed_ids, tenant_id=tenant_id):
        key = str(ghit["source"].get("document_id") or ghit["id"])
        if key not in merged:
            merged[key] = ghit

    results = list(merged.values())

    def _pass_filters(hit: dict) -> bool:
        src = hit.get("source") or {}
        if types and src.get("type") and src.get("type") not in types:
            return False
        if people:
            snippet = (hit.get("snippet") or "").lower()
            if not any(p.lower() in snippet for p in people):
                return False
        return True

    results = [r for r in results if _pass_filters(r)]
    results.sort(key=lambda r: r["score"], reverse=True)
    if settings.hybrid_rerank:
        results = _lexical_rerank(query, results)
    results = results[:limit]

    db.add(QueryLog(user_id=user_id, tenant_id=tenant_id, query_type="hybrid_search", query_text=query))
    db.commit()
    return results


def project_memory(db: Session, project_id: UUID, *, tenant_id: str | None = None) -> dict:
    q = db.query(Document).filter(Document.project_id == project_id)
    if tenant_id:
        q = q.filter(Document.tenant_id == tenant_id)
    docs = q.all()
    chunks = 0
    for d in docs:
        chunks += db.query(DocumentChunk).filter(DocumentChunk.document_id == d.id).count()
    return {
        "project_id": str(project_id),
        "documents": [{"id": str(d.id), "title": d.title, "source_system": d.source_system} for d in docs],
        "document_count": len(docs),
        "chunk_count": chunks,
    }
