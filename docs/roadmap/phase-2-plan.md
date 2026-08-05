# Phase 2 Plan — Unified Enterprise Knowledge Layer

**Status:** Draft after Phase 1 foundation  
**Prerequisite:** Phase 1 exit criteria met ([mvp.md](mvp.md))  
**Quality bar:** Every slice ships with unit and API tests (same standard as Phase 1).

---

## Goal

Create a connected organizational memory layer by integrating enterprise systems and deepening Decision, Project, Timeline, Expertise, and Freshness capabilities.

---

## Delivery slices (implement in order)

### P2-A — Connector framework

- Shared OAuth/token connector contract (see [../connectors/overview.md](../connectors/overview.md))
- Incremental sync cursors, ACL hints, health metrics
- Webhook receiver skeleton
- **Tests:** connector interface unit tests; mock sync producing canonical artifacts

### P2-B — Priority connectors

1. Slack  
2. GitHub  
3. Jira  
4. Google Drive  
5. Outlook / Gmail (email)  
6. Microsoft Teams  

- **Tests:** per-connector parse/normalize fixtures; auth error handling

### P2-C — Decision Memory depth

- Rich decision records linked to meetings, docs, PRs, tickets
- Expiration / supersedes workflows
- Assistant query templates (“Who approved…?”)
- **Tests:** extraction + graph edge assertions; API CRUD/ACL

### P2-D — Project Memory + Timeline

- Auto-link requirements, meetings, issues, releases into project graph
- Company timeline event model and API
- **Tests:** timeline ordering; project aggregation queries

### P2-E — Expertise Discovery + Knowledge Freshness

- Expert ranking from git/meetings/tickets/docs signals
- Freshness / trust / ownership scores + suggested updates
- **Tests:** scoring unit tests with synthetic activity; ranking stability

### P2-F — Advanced Search

- Hybrid retrieval (vector + keyword + graph expansion)
- Filters by source system, people, date, project
- **Tests:** hybrid ranking fixtures; ACL regression across sources

---

## Out of scope for Phase 2

- Predictive analytics, multi-agent research, RPA automation (Phase 3)
- Air-gapped certification
- Full ABAC (start with richer RBAC + source ACL inheritance)

---

## Exit criteria

- At least 3 connectors live in a pilot tenant  
- Decision and project views populated from real sync data  
- Expert discovery returns evidence-backed rankings  
- Freshness scores visible in UI/API  
- Test suite covers unit + API for each P2 slice; CI green without live SaaS secrets (mocks)

---

## Implementation note

Do not start Phase 2 slices until Phase 1 Slice E checklist in [mvp.md](mvp.md) is marked complete.
