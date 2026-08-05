# Product Requirements Document (PRD)

**Product:** Enterprise Brain  
**Version:** 1.0  
**Status:** Approved for design / MVP planning

---

## 1. Executive Summary

Enterprise Brain is an AI-powered organizational memory platform that connects meetings, emails, chat, documents, projects, source code, tickets, CRM, HR, calendars, and business applications into one continuously evolving knowledge graph.

Users ask natural language questions and receive trustworthy answers supported by verifiable evidence, timelines, relationships, and confidence scores.

**MVP goal:** Validate product-market fit by solving enterprise knowledge retrieval (auth, ingest, semantic search, AI chat, basic graph, RBAC, dashboard, API).

---

## 2. Goals & Non-Goals

### Goals (MVP)

- Ingest documents and meeting transcripts into a unified knowledge store  
- Provide semantic search and evidence-backed AI chat  
- Maintain a basic knowledge graph of people, projects, documents, and decisions  
- Enforce role-based access to knowledge  
- Expose REST APIs and an operator dashboard  

### Non-Goals (MVP)

- Full connector suite (Slack, Jira, etc. — Phase 2)  
- Predictive analytics and multi-agent automation (Phase 3)  
- Air-gapped production certification (supported later)  
- Full ABAC policy engine (RBAC first; ABAC Phase 2+)  

---

## 3. User Roles

| Role | Primary needs |
|------|----------------|
| Employee | Ask questions, find experts, retrieve docs |
| Manager | Team knowledge health, decisions, capacity |
| Project Manager | Project memory, risks, dependencies |
| Executive | Dashboards, decision velocity, strategic risks |
| Administrator | Users, tenants, connectors, config |
| Knowledge Manager | Freshness, ownership, curation |
| AI Administrator | Models, prompts, pipelines, evals |
| Auditor | Access logs, retention, compliance |

See [personas-and-roles.md](personas-and-roles.md).

---

## 4. Functional Requirements

### 4.1 Authentication & User Management

| ID | Requirement | Priority |
|----|-------------|----------|
| AUTH-01 | SSO via OAuth/OIDC (and SAML in Phase 2+) | P0 |
| AUTH-02 | Local/user management for admins | P0 |
| AUTH-03 | Role assignment (RBAC) | P0 |
| AUTH-04 | Session management & secure logout | P0 |

### 4.2 Document & Transcript Ingestion

| ID | Requirement | Priority |
|----|-------------|----------|
| ING-01 | Upload documents (PDF, DOCX, TXT, MD) | P0 |
| ING-02 | Ingest meeting transcripts (file or API) | P0 |
| ING-03 | Parse, chunk, embed, and index content | P0 |
| ING-04 | Extract entities and relations into graph | P0 |
| ING-05 | Attach source metadata and provenance | P0 |

### 4.3 Semantic Search

| ID | Requirement | Priority |
|----|-------------|----------|
| SRCH-01 | Natural language search over company knowledge | P0 |
| SRCH-02 | Hybrid retrieval (vector + keyword + graph) | P1 |
| SRCH-03 | Filter by project, date, people, source type | P1 |
| SRCH-04 | Return snippets with source citations | P0 |

### 4.4 AI Chat / Assistant

| ID | Requirement | Priority |
|----|-------------|----------|
| AI-01 | Chat over ingested knowledge | P0 |
| AI-02 | Answers include confidence and sources | P0 |
| AI-03 | Related people, projects, documents | P1 |
| AI-04 | Timeline context when applicable | P1 |
| AI-05 | Respect ACL on retrieved evidence | P0 |

### 4.5 Knowledge Graph

| ID | Requirement | Priority |
|----|-------------|----------|
| KG-01 | Core nodes: Employee, Project, Document, Meeting, Decision, Task | P0 |
| KG-02 | Core edges: Created, Assigned To, Discussed In, Related To, Belongs To | P0 |
| KG-03 | Graph visualization (basic) | P1 |
| KG-04 | Entity resolution & duplicate detection | P2 |
| KG-05 | Graph search API | P1 |

### 4.6 Permissions & Dashboard

| ID | Requirement | Priority |
|----|-------------|----------|
| SEC-01 | RBAC on documents, chat, admin | P0 |
| SEC-02 | Audit log of access and admin actions | P1 |
| DASH-01 | Overview: ingest stats, search usage, knowledge growth | P0 |
| DASH-02 | Admin user/role management UI | P0 |

### 4.7 API

| ID | Requirement | Priority |
|----|-------------|----------|
| API-01 | REST for auth, ingest, search, chat, graph | P0 |
| API-02 | OpenAPI specification | P0 |
| API-03 | Webhooks for ingest completion (Phase 2) | P2 |
| API-04 | GraphQL (Phase 2) | P2 |

---

## 5. Phase 2+ Functional Themes

Documented in detail under [modules/overview.md](../modules/overview.md) and [roadmap/phases.md](../roadmap/phases.md):

- Connectors (Slack, Teams, GitHub, Jira, Drive, Outlook, Gmail)  
- Decision Memory, Project Memory, Timeline, Expert Discovery, Knowledge Freshness  
- Predictive analytics, workflow intelligence, dependency graph, multi-agent research  

---

## 6. Non-Functional Requirements

| Category | Requirement |
|----------|-------------|
| Performance | Search P95 < 2s for typical corpora (MVP target) |
| Availability | 99.5% for SaaS MVP; higher for enterprise SLAs later |
| Scalability | Horizontal workers for ingest & embedding |
| Security | Encryption in transit (TLS) and at rest; secrets via vault |
| Privacy | Tenant isolation; optional private/local LLM path |
| Observability | Metrics, traces, structured logs |
| Usability | Evidence and confidence visible on every AI answer |

---

## 7. Success Metrics

See [problems-and-outcomes.md](problems-and-outcomes.md).

Primary MVP metrics:

- Search success rate  
- Knowledge retrieval time  
- AI answer confidence (user-rated)  
- Meeting / document coverage of pilot teams  

---

## 8. Constraints & Assumptions

- Pilot customers can provide sample documents and transcripts.  
- Cloud LLM (e.g. GPT-class) acceptable for MVP; local models optional later.  
- Neo4j + Qdrant + PostgreSQL as default data plane.  
- Single-tenant deployable for early enterprise pilots.

---

## 9. Open Questions

- Default auth provider for SaaS vs on-prem (Clerk vs Keycloak).  
- Retention defaults and legal hold workflows.  
- Graph visualization library beyond Cytoscape.js if needed at scale.  
- Evaluation harness for retrieval and answer quality.
