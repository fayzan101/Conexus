# Phase 4 Plan — Pilot Hardening

**Status:** Implemented on branch `phase-4-pilot-hardening`  
**Prerequisite:** Phases 1–3 foundation  
**Quality bar:** Unit + API tests; OAuth contract fixtures; RAG gold-set gates

## Slices

| Slice | Capability |
|-------|------------|
| Auth | OIDC bearer validation, refresh tokens, invites; block `AUTH_PROVIDER=dev` outside local |
| LLM / embeddings | OpenAI-compatible gateway + managed embeddings; versioned collections; faithfulness check |
| Connectors | Live Slack + GitHub OAuth, signed webhooks, rate-limit backoff (fixture mode retained) |
| Ingest queue | Redis (or memory) job queue, DLQ, admin retry |
| Pilot UX | Connector health, admin failed jobs, global error / empty states |
| Eval | RAG gold-set (N≥50) recall@5 + citation presence in CI |

## Out of scope (later phases)

- Full connector catalog live (Teams/Jira/Drive/…)
- Kafka multi-worker scale
- SAML/SCIM / ABAC (Phase 6)
- K8s / SLO platform (Phase 7)
