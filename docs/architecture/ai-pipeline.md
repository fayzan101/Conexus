# AI Processing Pipeline

Incoming data passes through ordered stages. Stages may be skipped when not applicable (e.g. OCR for plain text).

## Stages

| # | Stage | Description |
|---|-------|-------------|
| 1 | Parsing | Extract text/structure from files and API payloads |
| 2 | OCR | Extract text from images/scanned PDFs |
| 3 | Speech-to-text | Transcribe audio/video meetings |
| 4 | Entity extraction | Detect people, projects, systems, orgs, etc. |
| 5 | Relation extraction | Infer typed edges between entities |
| 6 | Topic detection | Themes / tags for clustering and search |
| 7 | Sentiment analysis | Tone signals (support, meetings, tickets) |
| 8 | Embedding generation | Chunk embeddings for vector search |
| 9 | Metadata generation | Titles, summaries, ACL hints, quality scores |
| 10 | Knowledge graph update | Upsert nodes/edges with provenance |

---

## Pipeline Architecture

```
Raw Object Store
      ↓
Parse / OCR / STT
      ↓
Normalize + Chunk
      ↓
Parallel: NER | Relations | Topics | Sentiment | Summary
      ↓
Embeddings
      ↓
Write: PostgreSQL metadata | Neo4j | Qdrant
      ↓
Post-process: freshness, duplicates, webhooks
```

---

## Chunking Guidelines (MVP)

- Prefer semantic/section-aware chunking for docs.  
- Meeting transcripts: chunk by speaker turns or time windows with overlap.  
- Keep chunk metadata: `document_id`, `offsets`, `speakers`, `meeting_id`, `acl`.

---

## Idempotency & Retries

- Jobs keyed by `(tenant_id, source_system, source_id, content_hash)`.  
- Reprocessing updates rather than duplicates.  
- Failed stages retry with backoff; poison queue for manual review.

---

## Quality Gates

| Gate | Action |
|------|--------|
| Empty extract | Flag for OCR/manual |
| Low NER confidence | Store provisional entities |
| ACL missing | Restrict to uploader/admins until classified |
| PII heuristics (later) | Redact or quarantine per policy |

---

## Phase Evolution

| Phase | Pipeline focus |
|-------|----------------|
| MVP | Parse, chunk, embed, basic NER/relations, graph upsert |
| Phase 2 | Live connectors, meeting STT, decision/project extractors |
| Phase 3 | Continuous scoring, anomaly detection, agentic research jobs |
