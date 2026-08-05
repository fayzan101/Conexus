from __future__ import annotations

import hashlib
from typing import Protocol

import httpx

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


class OpenAIEmbedder:
    """Managed embeddings via OpenAI-compatible /embeddings endpoint."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.dim = settings.embedding_dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if not self.settings.llm_api_key:
            # Fall back to hash if key missing (local)
            return HashEmbedder(dim=self.dim).embed(texts)

        base = self.settings.llm_base_url.rstrip("/")
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(
                f"{base}/embeddings",
                headers={
                    "Authorization": f"Bearer {self.settings.llm_api_key}",
                    "Content-Type": "application/json",
                },
                json={"model": self.settings.embedding_model, "input": texts},
            )
            resp.raise_for_status()
            data = resp.json()
            vectors = [row["embedding"] for row in sorted(data["data"], key=lambda r: r["index"])]
            # Truncate/pad to configured dim for collection compatibility
            out: list[list[float]] = []
            for vec in vectors:
                if len(vec) > self.dim:
                    vec = vec[: self.dim]
                elif len(vec) < self.dim:
                    vec = vec + [0.0] * (self.dim - len(vec))
                out.append(vec)
            return out


def get_embedder(settings: Settings) -> Embedder:
    provider = (settings.embedding_provider or "hash").lower()
    if provider in {"openai", "azure", "managed"}:
        return OpenAIEmbedder(settings)
    return HashEmbedder(dim=settings.embedding_dim)
