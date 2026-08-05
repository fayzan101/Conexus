# Personas & User Roles

## Roles

| Role | Access level | Typical actions |
|------|--------------|-----------------|
| Employee | Standard | Search, chat, view permitted sources, find experts |
| Manager | Elevated | Team knowledge views, decisions, capacity signals |
| Project Manager | Project-scoped | Project memory, risks, timelines, dependencies |
| Executive | Org-wide (permitted) | Dashboards, strategic Q&A, decision velocity |
| Administrator | Tenant admin | Users, roles, connectors, settings |
| Knowledge Manager | Curation | Freshness, ownership, merge duplicates, policies |
| AI Administrator | Platform AI | Models, prompts, pipelines, evaluation, quotas |
| Auditor | Read-only audit | Access logs, retention, compliance reports |

---

## Personas (MVP)

### Alex — Individual Contributor

- Needs: “Who decided X?”, “Where is the latest design for Y?”  
- Pain: Searches Slack, Drive, Confluence separately  
- Success: One chat answer with links and confidence  

### Jordan — Engineering Manager

- Needs: Project status context, who owns a subsystem, onboarding help  
- Pain: Knowledge siloed in senior engineers  
- Success: Expertise discovery + project memory  

### Sam — Knowledge / Ops Lead

- Needs: Coverage of meetings and docs, stale content flags  
- Pain: Manual wiki gardening  
- Success: Freshness scores and suggested updates  

### Riley — Tenant Administrator

- Needs: SSO, roles, upload pipelines, dashboards  
- Pain: Tool sprawl and access chaos  
- Success: Central RBAC and ingest health metrics  

---

## Permission Principles

1. **Least privilege** — default deny on sensitive sources.  
2. **Source ACL inheritance** — chat/search only returns evidence the user may see.  
3. **Separation of duties** — AI Admin ≠ Auditor; Admin ≠ unrestricted data export without audit.  
4. **Explainability** — when access blocks an answer, say so without leaking content.

Detailed matrices: [../security/access-control.md](../security/access-control.md).
