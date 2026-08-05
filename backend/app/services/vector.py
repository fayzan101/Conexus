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
    ) -> list[dict]:
        self.ensure_collection()
        query_filter = None
        if project_id:
            query_filter = qm.Filter(
                must=[qm.FieldCondition(key="project_id", match=qm.MatchValue(value=str(project_id)))]
            )
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
