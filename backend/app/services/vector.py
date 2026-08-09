from __future__ import annotations

from uuid import UUID

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from app.config import Settings


class VectorStore:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = QdrantClient(url=settings.qdrant_url, prefer_grpc=False)
        self.collection = settings.versioned_collection
        self.dim = settings.embedding_dim

    def ensure_collection(self) -> None:
        names = {c.name for c in self.client.get_collections().collections}
        if self.collection in names:
            return
        self.client.create_collection(
            collection_name=self.collection,
            vectors_config=qm.VectorParams(size=self.dim, distance=qm.Distance.COSINE),
        )

    def upsert(
        self,
        *,
        point_id: str,
        vector: list[float],
        payload: dict,
    ) -> None:
        self.ensure_collection()
        self.client.upsert(
            collection_name=self.collection,
            points=[
                qm.PointStruct(id=point_id, vector=vector, payload=payload),
            ],
        )

    def search(
        self,
        *,
        vector: list[float],
        limit: int = 10,
        project_id: UUID | None = None,
        tenant_id: str | None = None,
    ) -> list[dict]:
        self.ensure_collection()
        must = []
        if project_id:
            must.append(qm.FieldCondition(key="project_id", match=qm.MatchValue(value=str(project_id))))
        if tenant_id:
            must.append(qm.FieldCondition(key="tenant_id", match=qm.MatchValue(value=tenant_id)))
        query_filter = qm.Filter(must=must) if must else None
        hits = self.client.search(
            collection_name=self.collection,
            query_vector=vector,
            limit=limit,
            query_filter=query_filter,
        )
        return [
            {
                "id": str(hit.id),
                "score": float(hit.score),
                "payload": hit.payload or {},
            }
            for hit in hits
        ]

    def delete(self, *, point_id: str) -> None:
        try:
            self.ensure_collection()
            self.client.delete(
                collection_name=self.collection,
                points_selector=qm.PointIdsList(points=[point_id]),
            )
        except Exception:
            pass
