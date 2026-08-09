# Phase 5 Plan — Scale & Knowledge Quality

**Status:** Implemented on branch `phase-5-scale-quality`  
**Prerequisite:** Phase 4 pilot hardening  
**Quality bar:** Unit + API tests; tenant isolation suite; hybrid retrieval gates

## Slices

| Slice | Capability |
|-------|------------|
| Connectors | Live OAuth/sync for Teams, Jira, Google Drive, Outlook, Gmail (fixture mode retained) |
| Event bus | Kafka-ready publisher with memory fallback; queue depth / backpressure metrics |
| Retrieval v2 | Postgres FTS (SQLite fallback), bounded graph expansion, optional lexical rerank |
| Entity resolution | People/project alias merge + supersedes audit trail |
| Memory links | Auto-propose decision/project links with confidence + human confirm |
| Multi-tenancy | Hard `tenant_id` on core rows + vector/graph payloads; envelope key registry |

## Out of scope (later)

- Full OpenSearch cluster
- Trained cross-encoder reranker
- SAML/SCIM / ABAC (Phase 6)
- K8s / SLO platform (Phase 7)
