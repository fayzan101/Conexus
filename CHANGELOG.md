# Changelog

All notable changes to Enterprise Brain will be documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/).  
This project follows semantic versioning once the first public API is tagged.

## [Unreleased]

### Added

- Phase 1 implementation slices A–E with unit/API tests
  - Neon/Alembic schema bootstrap, SQLite test harness
  - Document parsers (text/PDF/DOCX), projects CRUD
  - ACL-aware search, grounded chat + optional OpenAI LLM
  - Graph neighbor UI, RBAC tests, pilot smoke script
  - Phase 2 plan (`docs/roadmap/phase-2-plan.md`)
- MVP codebase scaffold
  - FastAPI backend (auth, users, documents, meetings, search, chat, graph, decisions, metrics)
  - Next.js frontend (login, dashboard, search, chat, ingest, graph, decisions, admin)
  - Docker Compose (Postgres, Neo4j, Qdrant, Redis, MinIO)
  - Alembic migration, CI workflow, Makefile
- Project Proposal PDF (`docs/product/Enterprise-Brain-Project-Proposal.pdf`)
- Initial product and engineering documentation suite (v1.0 design)

## [1.0.0-docs] — 2026-08-05

### Added

- Documentation baseline for Enterprise Brain platform design
