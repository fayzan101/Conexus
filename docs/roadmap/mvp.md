# MVP Scope (Phase 1)

**Duration:** 2–3 months  
**Goal:** Validate PMF via enterprise knowledge retrieval

---

## In Scope

| Area | Deliverable |
|------|-------------|
| Auth | SSO or managed auth; sessions/JWT |
| Users | Invite, roles (Employee, Admin minimum) |
| Ingest | Document upload + meeting transcript API/upload |
| Pipeline | Parse → chunk → embed → basic NER/relations → index |
| Search | Semantic search with citations |
| Assistant | Grounded chat with confidence + sources |
| Graph | Core nodes/edges + basic viz + API |
| Security | RBAC on API/UI; TLS |
| Dashboard | Ingest health, counts, admin users |
| API | REST + OpenAPI |

---

## Out of Scope (defer)

- Full connector suite  
- Live meeting transcription productization  
- ABAC  
- Predictive analytics / multi-agent research  
- GraphQL & webhooks (optional stretch)  
- Air-gapped certification  

---

## Suggested Workstreams

1. **Platform** — monorepo, Compose, CI, auth  
2. **Ingest** — upload, workers, MinIO, job status  
3. **Retrieval** — Qdrant + search API  
4. **Graph** — Neo4j schema + upsert  
5. **Assistant** — RAG chat + answer contract  
6. **Web** — login, upload, search, chat, graph view, admin  

---

## Exit Criteria

- Pilot team can upload ≥ N docs and transcripts  
- Gold-set search meets agreed recall/precision targets  
- Chat answers cite sources; ACL test cases pass  
- Admin can manage users/roles  
- OpenAPI published; basic load test on search/chat  

---

## Risks

| Risk | Mitigation |
|------|------------|
| LLM cost/latency | Caching, smaller models for classify |
| Extraction quality | Human-editable decisions/entities |
| Scope creep | Lock Phase 2 connectors out of MVP |
| ACL bugs | Automated ACL regression suite |

Related: [../modules/mvp-modules.md](../modules/mvp-modules.md), [../product/prd.md](../product/prd.md)
