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

## Implementation checklist (Slice E)

| Criterion | Status |
|-----------|--------|
| Neon/Postgres schema via Alembic + auto-migrate on startup | Done |
| Dev JWT auth + seeded admin/employee | Done |
| Document + transcript ingest with text/PDF/DOCX parsers | Done |
| Projects CRUD for linking uploads | Done |
| Semantic search + ACL filter for private docs | Done |
| Grounded chat (LLM when `LLM_API_KEY` set; stub otherwise) | Done |
| Graph API + UI neighbor expansion | Done |
| Admin user invite + RBAC 403 tests | Done |
| Unit + API tests in CI (no live secrets required) | Done |
| Phase 2 plan drafted | Done — see [phase-2-plan.md](phase-2-plan.md) |

### Pilot path (manual)

1. `docker compose up -d neo4j qdrant redis minio minio-init`  
2. Configure Neon `DATABASE_URL` in `.env`  
3. Start API + web  
4. Login as admin → create project → upload text/PDF → ingest transcript  
5. Search + chat should return citations; graph shows Document/Meeting nodes  

---

## Out of Scope (defer)

- Full connector suite  
- Live meeting transcription productization  
- ABAC  
- Predictive analytics / multi-agent research  
- GraphQL & webhooks (optional stretch)  
- Air-gapped certification  

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

Related: [../modules/mvp-modules.md](../modules/mvp-modules.md), [../product/prd.md](../product/prd.md), [phase-2-plan.md](phase-2-plan.md)
