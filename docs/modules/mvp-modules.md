# MVP Module Specifications

Acceptance-oriented specs for Phase 1 (2–3 months).

---

## M1 – Basic Knowledge Graph

**In scope**

- Upsert Employee, Project, Document, Meeting, Decision, Task  
- Edges: Created, Assigned To, Discussed In, Related To, Belongs To, Approved By, References  
- Graph query API (neighbors, path of length ≤ 3)  
- Simple visualization in UI  

**Acceptance**

- Given an uploaded doc mentioning a project and owner, graph contains linked nodes within processing SLA.  
- User can open a project node and see related documents/meetings.

---

## M2 – Meeting Memory (MVP)

**In scope**

- Upload / API ingest of transcripts  
- Summary + action items + decisions extraction  
- Link meeting to project when detectable  

**Out of scope**

- Live transcription, speaker diarization accuracy guarantees  

**Acceptance**

- Transcript produces Summary, Tasks, Decisions artifacts stored with provenance.

---

## M3 – Decision Intelligence (MVP)

**In scope**

- Manual + extracted Decision records with owner/date/status/context  
- Searchable via assistant (“Who approved…?”) when evidence exists  

**Acceptance**

- Decision detail page shows evidence links and approver when present.

---

## M9 – Enterprise Search (MVP)

**In scope**

- Semantic search over documents and transcripts  
- Filters: date range, project (if tagged)  
- Citation snippets  

**Acceptance**

- Top-5 results include at least one relevant source on gold-set queries (≥ target recall@5).

---

## M14 – AI Assistant (MVP)

**In scope**

- Multi-turn chat grounded in retrieved evidence  
- Confidence + sources on every answer  
- ACL enforcement  

**Acceptance**

- Answers refuse or hedge without evidence.  
- Forbidden documents never appear in sources for unauthorized users.

---

## M15 – Dashboard (MVP)

**In scope**

- Ingest job health, document counts, query volume, user admin  

**Acceptance**

- Admin can invite user, assign role, view ingest failures.

---

## Cross-Cutting MVP

| Area | Requirement |
|------|-------------|
| Auth | Login via chosen IdP; JWT/session to API |
| RBAC | Employee / Admin minimum roles |
| API | OpenAPI for ingest, search, chat, graph |
| Storage | Raw files in object store; metadata in Postgres |
