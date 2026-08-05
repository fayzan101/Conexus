# Access Control (RBAC & ABAC)

## RBAC (MVP)

### Roles

| Role | Capabilities |
|------|----------------|
| Employee | Search/chat on permitted knowledge; view own profile |
| Manager | Employee + team-scoped dashboards |
| Project Manager | Project-scoped resources |
| Executive | Org dashboards (permitted metrics) |
| Administrator | Users, roles, connectors, tenant settings |
| Knowledge Manager | Curation, freshness actions, merges |
| AI Administrator | Model/prompt/pipeline config |
| Auditor | Read audit logs & compliance reports |

Roles are additive; deny wins on conflicts.

---

## Resource Permissions (MVP Matrix)

| Resource | Employee | Admin | Auditor | AI Admin |
|----------|----------|-------|---------|----------|
| Search permitted docs | ✓ | ✓ | — | ✓ |
| Upload docs | ✓* | ✓ | — | ✓ |
| Manage users | — | ✓ | — | — |
| View audit logs | — | ✓ | ✓ | — |
| Configure models | — | — | — | ✓ |
| Delete tenant data | — | ✓ | — | — |

\*May be restricted by tenant policy.

---

## ABAC (Phase 2+)

Attributes may include: department, project membership, data classification, geography, employment status, source system.

Example policy intent:

> Allow read if `user.projects` contains `resource.project_id` OR `resource.classification == public`.

---

## Retrieval Enforcement

1. Candidate retrieval from vector/graph.  
2. Filter by ACL service.  
3. Generate only from remaining evidence.  
4. If empty → “insufficient accessible evidence” response.

---

## API Keys & Service Accounts

- Scoped keys for automation (ingest, search).  
- Rotatable; shown once at creation.  
- Bound to tenant and role subset.
