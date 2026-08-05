# PR: Phase 2 — Enterprise Intelligence Layer

**Branch:** `phase-2-enterprise-intelligence` → `main`  
**Open PR:** https://github.com/fayzan101/Conexus/compare/main...phase-2-enterprise-intelligence?expand=1

---

## Summary

- Add Phase 2 connector framework and priority adapters (Slack, GitHub, Jira, Google Drive, Outlook, Gmail, Teams) with sync + webhook skeleton and fixture-based pilot mode.
- Deepen Decision Memory (links, supersedes, who-approved query), Project Memory + Timeline APIs/UI, Expertise Discovery and Knowledge Freshness scoring.
- Ship hybrid search (vector + keyword) with filters, frontend pages for Connectors/Timeline/Expertise, Alembic `0002`, and unit/API tests for each slice.

## Test plan

- [ ] `cd backend && pytest -q -m "not integration"`
- [ ] Connect Slack (or GitHub) via `/connectors` with fixture JSON and confirm timeline + documents appear
- [ ] Create a decision with links; call `/v1/decisions/query/who-approved?q=...`
- [ ] Open Timeline and Expertise pages; refresh freshness scores
- [ ] Run hybrid search from Search UI and confirm retrieval mode labels
- [ ] Confirm CI green on `phase-2-enterprise-intelligence`
