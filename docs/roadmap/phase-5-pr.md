# Phase 5 PR — Scale & Knowledge Quality

**Branch:** `phase-5-scale-quality`  
**Compare:** `phase-4-pilot-hardening...phase-5-scale-quality`

## Summary

- **Connectors:** Live OAuth/sync paths for Teams, Jira, Google Drive, Outlook, Gmail (fixture mode retained)
- **Event bus:** Kafka-ready publisher with memory fallback + backpressure metrics (`/v1/knowledge/events/metrics`)
- **Retrieval v2:** Postgres FTS (ILIKE fallback), optional graph expansion, lexical rerank
- **Entity resolution:** Canonical entities, duplicate detection, merge with supersedes audit
- **Memory links:** Auto-propose decision/project links with confidence + human confirm APIs
- **Multi-tenancy:** Hard `tenant_id` on core tables; vector/graph payload isolation; envelope DEK registry
- **Schema:** Alembic `0005`

## Test plan

- [ ] `cd backend && .venv/Scripts/python.exe -m pytest -m "not integration"`
- [ ] Create project/document as tenant A; ensure tenant B search cannot see it
- [ ] `POST /v1/knowledge/entities` + merge duplicates
- [ ] Connector OAuth start for teams/jira/google_drive returns authorize URL when client IDs set
- [ ] Hybrid search mode returns results with `retrieval` metadata

## Exit criteria

- [ ] All priority connectors have live OAuth/sync paths  
- [ ] Zero cross-tenant leakage in isolation tests  
- [ ] Hybrid v2 + entity/memory APIs available  
