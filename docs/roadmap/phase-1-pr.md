# PR: Phase 1 — Foundation platform (MVP)

**Branch:** `phase-1-foundation` → `main`  
**Open PR:** https://github.com/fayzan101/Conexus/compare/main...phase-1-foundation?expand=1

---

## Summary

- Complete Phase 1 (Foundation) MVP slices: Neon/Alembic schema bootstrap, document/transcript ingest with text/PDF/DOCX parsers, projects CRUD, ACL-aware semantic search, grounded chat (optional LLM), graph neighbor UI, and admin RBAC.
- Expand automated coverage with SQLite unit/API tests and CI (`pytest -m "not integration"`); add pilot smoke script and Phase 2 plan doc for the next branch.
- Document phase delivery convention: one branch + PR per phase (`phase-1-foundation`, then `phase-2-enterprise-intelligence`, etc.).

## Test plan

- [ ] `cd backend && pytest -q -m "not integration"`
- [ ] Start Neo4j/Qdrant/Redis/MinIO via Compose; run API against Neon `DATABASE_URL`
- [ ] Login as admin, create project, upload a text doc and transcript
- [ ] Verify search citations and chat confidence/sources
- [ ] Tap a graph node and confirm neighbor edges render
- [ ] Confirm employee gets 403 on `GET /v1/users`; admin can invite users
- [ ] Confirm CI workflow passes on this branch
