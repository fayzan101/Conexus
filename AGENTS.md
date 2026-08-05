# Agent Guide (Enterprise Brain / Cognexus)

Instructions for AI coding agents working in this repository.

## Product Intent

Build an **organizational memory** platform—not a generic chatbot or file dump. Answers must be **evidence-backed** (sources + confidence). Never bypass **tenant isolation** or **ACL** filters in retrieval or generation.

## Doc Map

Start here: [docs/README.md](docs/README.md)

| If you are… | Read |
|-------------|------|
| Implementing MVP | [docs/roadmap/mvp.md](docs/roadmap/mvp.md), [docs/modules/mvp-modules.md](docs/modules/mvp-modules.md) |
| Touching graph schema | [docs/architecture/data-model.md](docs/architecture/data-model.md) |
| Touching ingest/RAG | [docs/architecture/ai-pipeline.md](docs/architecture/ai-pipeline.md), [docs/architecture/ai-architecture.md](docs/architecture/ai-architecture.md) |
| Adding APIs | [docs/api/rest.md](docs/api/rest.md) |
| Auth / permissions | [docs/security/access-control.md](docs/security/access-control.md) |

## Phase delivery

- Use a **separate git branch per phase** (e.g. `phase-1-foundation` … `phase-8-ga-maturity`).
- When phase work ends, open a **PR with Summary + Test plan**. Do not merge multiple phases in one PR.
- Maturity path after Phase 3: [docs/roadmap/production-maturity-plan.md](docs/roadmap/production-maturity-plan.md).
- See [CONTRIBUTING.md](CONTRIBUTING.md).


1. Scope work to the active phase unless the user expands scope.  
2. Prefer adapters for Neo4j/Qdrant/LLM providers.  
3. Every chat/search path: retrieve → ACL filter → generate.  
4. Update docs when changing contracts or module scope.  
5. Do not commit secrets; use `.env.example` as the template.  

## Answer Contract (Assistant)

Responses should support: `answer`, `confidence`, `sources`, `related_documents`, `related_projects`, `people_involved`, `timeline`, `supporting_evidence`.

## Stack Defaults

See [docs/architecture/tech-stack.md](docs/architecture/tech-stack.md) and [ADR 0002](docs/architecture/adr/0002-mvp-data-plane.md).
