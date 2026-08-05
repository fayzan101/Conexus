# Product Roadmap

## Phase 1 — MVP (2–3 Months)

**Goal:** Validate product-market fit by solving enterprise knowledge retrieval.

Deliverables:

- Authentication  
- User management  
- Document upload  
- Meeting transcript ingestion  
- Semantic search  
- AI chat over company knowledge  
- Basic knowledge graph  
- Role-based permissions  
- Dashboard  
- API  

Details: [mvp.md](mvp.md)

---

## Phase 2 — Unified Enterprise Knowledge Layer

**Goal:** Create a unified enterprise knowledge layer.

### Integrations

Slack, Teams, GitHub, Jira, Google Drive, Outlook, Gmail

### Capabilities

- Decision Memory  
- Project Memory  
- Timeline  
- Expert Discovery  
- Knowledge Freshness  
- Advanced Search  

---

## Phase 3 — AI Operating System

**Goal:** Transform Enterprise Brain into an AI operating system for organizations.

- Predictive Analytics  
- Workflow Intelligence  
- Business Dependency Graph  
- Executive Dashboards  
- Multi-Agent AI  
- Automation Engine  
- Recommendation Engine  
- Forecasting  
- Opportunity Discovery  

**Status:** Foundation implemented on `phase-3-ai-operating-system` (heuristic / pilot-quality).

---

## Phases 4–8 — Production Maturity (to 100%)

The foundation (Phases 1–3) is **not** production-complete. Continues here:

**[production-maturity-plan.md](production-maturity-plan.md)**

| Phase | Focus | Branch |
|-------|--------|--------|
| 4 | Pilot hardening (SSO, live LLM, 2 live connectors, async ingest) | `phase-4-pilot-hardening` |
| 5 | Scale & knowledge quality (all priority connectors, multi-tenant, retrieval v2) | `phase-5-scale-quality` |
| 6 | Enterprise security (SAML/SCIM, ABAC, retention, private LLM, AppSec) | `phase-6-enterprise-security` |
| 7 | Platform ops (K8s, SLOs, DR, IaC, multi-deploy) | `phase-7-platform-ops` |
| 8 | GA / 100% maturity (ML+agents GA, automation, compliance pack, SLAs) | `phase-8-ga-maturity` |

---

## Future Vision

Evolve from enterprise search into an AI-powered operating system for organizational intelligence—proactively surfacing risks, recommending actions, automating workflows, and preserving institutional knowledge across the business lifecycle.

After Phase 8 GA, future work expands connector catalog (CRM/ERP/HR), deeper domain packs, and continuous model improvement—without blocking the production-maturity definition above.
