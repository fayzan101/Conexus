from __future__ import annotations

import hashlib
from typing import Protocol

from app.config import Settings


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class HashEmbedder:
    """Deterministic local embedder for MVP without ML deps."""

    def __init__(self, dim: int = 384):
        self.dim = dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            vec = [0.0] * self.dim
            tokens = text.lower().split()
            if not tokens:
                vectors.append(vec)
                continue
            for token in tokens:
                digest = hashlib.sha256(token.encode("utf-8")).digest()
                for i in range(0, min(len(digest), self.dim // 4)):
                    idx = (digest[i] + i * 17) % self.dim
                    sign = 1.0 if digest[-(i + 1)] % 2 == 0 else -1.0
                    vec[idx] += sign
            norm = sum(v * v for v in vec) ** 0.5 or 1.0
            vectors.append([v / norm for v in vec])
        return vectors


def get_embedder(settings: Settings) -> Embedder:
    # Future: sentence-transformers / OpenAI adapters
    return HashEmbedder(dim=settings.embedding_dim)
