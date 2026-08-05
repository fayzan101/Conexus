from __future__ import annotations

import httpx

from app.config import Settings


def synthesize_with_llm(settings: Settings, *, query: str, evidence: list[dict]) -> str | None:
    """Call OpenAI-compatible chat API when LLM_API_KEY is configured."""
    if not settings.llm_api_key:
        return None

    context_blocks = []
    for i, item in enumerate(evidence, start=1):
        title = item.get("title") or "Untitled"
        snippet = item.get("snippet") or ""
        context_blocks.append(f"[{i}] {title}\n{snippet}")
    context = "\n\n".join(context_blocks)

    system = (
        "You are Enterprise Brain, an organizational memory assistant. "
        "Answer ONLY using the provided evidence. If evidence is insufficient, say so. "
        "Cite sources as [n]. Be concise and factual."
    )
    user = f"Question: {query}\n\nEvidence:\n{context}"

    try:
        with httpx.Client(timeout=45.0) as client:
            resp = client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.llm_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.llm_model,
                    "temperature": 0.2,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


def stub_synthesize(*, query: str, hits: list[dict]) -> str:
    snippets = [h["snippet"] for h in hits if h.get("snippet")]
    answer = f"Based on {len(hits)} evidence source(s) for “{query}”: " + " ".join(snippets[:2])
    if len(answer) > 1200:
        answer = answer[:1200] + "…"
    return answer
