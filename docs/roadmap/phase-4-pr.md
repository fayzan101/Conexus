# Phase 4 PR — Pilot Hardening

**Branch:** `phase-4-pilot-hardening`  
**Compare:** `main...phase-4-pilot-hardening` (or `phase-3-ai-operating-system...phase-4-pilot-hardening`)

## Summary

- **Auth:** OIDC exchange + JWKS validation path; refresh tokens; invite create/accept; `AUTH_PROVIDER=dev` blocked outside local/test/development
- **LLM / embeddings:** OpenAI-compatible `LLM_BASE_URL`; managed embeddings provider; versioned Qdrant collections; answer faithfulness citation gate
- **Connectors:** Live Slack + GitHub OAuth start/callback, signed webhooks, rate-limit backoff; fixture mode retained; connector health API/UI
- **Ingest:** Redis/memory job queue, worker entrypoint, dead-letter + admin retry
- **UX:** Connector health, admin DLQ, invite page, global `error.tsx`
- **Tests:** OAuth contract fixtures, queue/auth/faithfulness unit tests, RAG gold-set (N≥50) recall/citation gates
- **Schema:** Alembic `0004`

## Test plan

- [ ] `cd backend && pytest -m "not integration"`
- [ ] Dev login + refresh token still works with `AUTH_PROVIDER=dev` + `ENVIRONMENT=local`
- [ ] Admin invite → `/invite?token=…` accept flow
- [ ] Upload document enqueues job (inline locally); failed jobs appear under Admin → Retry
- [ ] Connectors: fixture sync + health page; OAuth start returns URL when client IDs set
- [ ] Webhook signature rejects bad Slack/GitHub signatures when secrets configured

## Exit criteria (pilot)

- [ ] One pilot tenant can use OIDC (or local staging)  
- [ ] Slack + GitHub live path configured (or fixture until secrets land)  
- [ ] Chat answers include citations on gold set  
- [ ] Ingest queue + DLQ operational  
