# Enterprise Brain Documentation

Central index for product, architecture, API, security, and operations documentation.

**Product:** Enterprise Brain (Cognexus)  
**Version:** 1.0  
**Status:** Pre-implementation / Design complete

---

## Getting Started

| Doc | Audience |
|-----|----------|
| [../README.md](../README.md) | Everyone — product overview |
| [product/vision.md](product/vision.md) | Stakeholders — vision & mission |
| [product/project-proposal.md](product/project-proposal.md) | Project proposal (+ [PDF](product/Enterprise-Brain-Project-Proposal.pdf)) |
| [roadmap/mvp.md](roadmap/mvp.md) | Product & eng — Phase 1 scope |
| [deployment/overview.md](deployment/overview.md) | Ops — how to run |

---

## Product

| Doc | Description |
|-----|-------------|
| [product/vision.md](product/vision.md) | Vision, mission, principles |
| [product/prd.md](product/prd.md) | Product requirements document |
| [product/problems-and-outcomes.md](product/problems-and-outcomes.md) | Problems solved & success metrics |
| [product/personas-and-roles.md](product/personas-and-roles.md) | User roles & personas |
| [modules/overview.md](modules/overview.md) | All 15 functional modules |
| [modules/mvp-modules.md](modules/mvp-modules.md) | MVP module deep-dives |

---

## Architecture

| Doc | Description |
|-----|-------------|
| [architecture/overview.md](architecture/overview.md) | High-level system architecture |
| [architecture/data-model.md](architecture/data-model.md) | Knowledge graph nodes & edges |
| [architecture/ai-pipeline.md](architecture/ai-pipeline.md) | Ingestion & AI processing |
| [architecture/tech-stack.md](architecture/tech-stack.md) | Technology choices |
| [architecture/ai-architecture.md](architecture/ai-architecture.md) | LLMs, embeddings, ML |
| [architecture/adr/](architecture/adr/) | Architecture Decision Records |
| [glossary.md](glossary.md) | Shared terminology |

---

## Integrations

| Doc | Description |
|-----|-------------|
| [connectors/overview.md](connectors/overview.md) | Connector catalog & roadmap |

---

## API & SDKs

| Doc | Description |
|-----|-------------|
| [api/overview.md](api/overview.md) | API surface (REST, GraphQL, webhooks) |
| [api/rest.md](api/rest.md) | REST endpoint reference |
| [api/graphql.md](api/graphql.md) | GraphQL schema outline |
| [api/webhooks.md](api/webhooks.md) | Webhook events |
| [api/sdks.md](api/sdks.md) | Python, JS, Go, Java SDKs |

---

## Security & Compliance

| Doc | Description |
|-----|-------------|
| [security/overview.md](security/overview.md) | Security model |
| [security/access-control.md](security/access-control.md) | RBAC & ABAC |
| [security/compliance.md](security/compliance.md) | Retention, audit, compliance |

---

## Roadmap & Delivery

| Doc | Description |
|-----|-------------|
| [roadmap/phases.md](roadmap/phases.md) | Phase 1–3 roadmap |
| [roadmap/mvp.md](roadmap/mvp.md) | MVP (2–3 months) detail |
| [roadmap/phase-2-plan.md](roadmap/phase-2-plan.md) | Phase 2 plan (post–Phase 1) |
| [roadmap/phase-2-pr.md](roadmap/phase-2-pr.md) | Phase 2 PR description |
| [roadmap/phase-3-plan.md](roadmap/phase-3-plan.md) | Phase 3 plan |
| [roadmap/phase-3-pr.md](roadmap/phase-3-pr.md) | Phase 3 PR description |
| [roadmap/production-maturity-plan.md](roadmap/production-maturity-plan.md) | Phases 4–8 to 100% production maturity |
| [roadmap/phase-4-plan.md](roadmap/phase-4-plan.md) | Phase 4 plan |
| [roadmap/phase-4-pr.md](roadmap/phase-4-pr.md) | Phase 4 PR description |

---

## Operations

| Doc | Description |
|-----|-------------|
| [deployment/overview.md](deployment/overview.md) | Deployment options |
| [deployment/environments.md](deployment/environments.md) | Env config & secrets |
| [operations/monitoring.md](operations/monitoring.md) | Observability |
| [operations/runbook.md](operations/runbook.md) | Ops runbook outline |

---

## Development

| Doc | Description |
|-----|-------------|
| [../CONTRIBUTING.md](../CONTRIBUTING.md) | Contributing guide |
| [development/coding-standards.md](development/coding-standards.md) | Standards & conventions |
| [development/local-setup.md](development/local-setup.md) | Local development |

---

## Document Conventions

- Prefer absolute links within `docs/` using paths relative to this index.
- Version docs with the product version; note breaking API changes in [api/overview.md](api/overview.md).
- Keep module specs aligned with [modules/overview.md](modules/overview.md).
