# Knowledge Graph Data Model

## Purpose

Represent organizational knowledge as typed nodes and edges so AI can reason over people, work, decisions, and systems—not only documents.

---

## Core Node Types

| Node | Description |
|------|-------------|
| Employee | Person in the organization |
| Department | Org unit |
| Meeting | Scheduled or ad-hoc meeting |
| Project | Initiative or delivery effort |
| Task | Action item / work item |
| Decision | Recorded decision with context |
| Requirement | Product or system requirement |
| Document | File, page, or artifact |
| Policy | Policy or standard |
| Client | Customer / account |
| Vendor | External supplier |
| Repository | Source code repository |
| Pull Request | Code change proposal |
| Issue | Ticket / bug / request |
| Feature | Product feature |
| Incident | Operational incident |
| Server | Compute / host |
| API | Service API |
| Database | Data store |
| Invoice | Billing document |
| Contract | Legal agreement |
| Risk | Identified risk |
| Objective | Goal / OKR |
| Event | Timeline event |

### MVP Node Subset

`Employee`, `Project`, `Document`, `Meeting`, `Decision`, `Task`, `Department`

---

## Edge Types

| Edge | Semantics |
|------|-----------|
| Created | Author / originator |
| Assigned To | Ownership of work |
| Discussed In | Topic raised in meeting/doc |
| Approved By | Formal approval |
| References | Citation / link |
| Depends On | Hard dependency |
| Related To | Soft association |
| Owns | Accountability |
| Blocked By | Blocking relationship |
| Implements | Code/feature implements requirement |
| Requested By | Requester |
| Resolved By | Resolver |
| Supersedes | Newer version replaces older |
| Belongs To | Membership / containment |
| Verified By | Validation / review |

### MVP Edge Subset

`Created`, `Assigned To`, `Discussed In`, `Related To`, `Belongs To`, `Approved By`, `References`

---

## Example Patterns

### Decision

```
(Decision)-[:APPROVED_BY]->(Employee)
(Decision)-[:BELONGS_TO]->(Project)
(Decision)-[:REFERENCES]->(Document)
(Decision)-[:DISCUSSED_IN]->(Meeting)
(Decision)-[:SUPERSEDES]->(Decision)
```

### Meeting Memory

```
(Meeting)-[:BELONGS_TO]->(Project)
(Employee)-[:CREATED|ATTENDED]->(Meeting)
(Task)-[:DISCUSSED_IN]->(Meeting)
(Decision)-[:DISCUSSED_IN]->(Meeting)
(Document)-[:REFERENCES]->(Meeting)
```

### Expertise

```
(Employee)-[:OWNS|RESOLVED_BY|CREATED]->(Issue|PullRequest|Document|Decision)
```

---

## Properties (Common)

Every node should support:

| Property | Notes |
|----------|-------|
| `id` | Stable UUID |
| `tenant_id` | Multi-tenant isolation |
| `name` / `title` | Display label |
| `created_at` / `updated_at` | Timestamps |
| `source_system` | Origin connector or upload |
| `source_uri` | Deep link when available |
| `acl` / `visibility` | Access hints synchronized with ACL service |
| `confidence` | Extraction confidence (0–1) |
| `embedding_ref` | Optional pointer to vector ids |

Decision-specific (Module 3):

`owner`, `approver`, `date`, `context`, `evidence`, `alternatives`, `expected_outcome`, `status`, `expiration_date`

---

## Entity Resolution

- Normalize emails, names, and external IDs.  
- Merge duplicates with audit trail (`Supersedes` / merge events).  
- Prefer deterministic keys from source systems (e.g. Jira issue key, GitHub node_id).

---

## Graph + Vector Duality

| Concern | Store |
|---------|-------|
| Structure, multi-hop, “who/what/when” | Knowledge graph |
| Semantic similarity, paraphrases | Vector DB |
| Authoritative app state | PostgreSQL |

Retrieval combines both; see [ai-pipeline.md](ai-pipeline.md) and [ai-architecture.md](ai-architecture.md).
