# ADR 0001: Record Architecture Decisions

## Status

Accepted

## Context

Enterprise Brain has many significant technology and design choices (graph DB, vector DB, auth provider, LLM strategy). Without a lightweight decision log, rationale will be lost.

## Decision

Use Architecture Decision Records (ADRs) under `docs/architecture/adr/`.

- Number sequentially: `0001-title.md`, `0002-…`
- Each ADR includes: Status, Context, Decision, Consequences
- Status values: Proposed, Accepted, Deprecated, Superseded

## Consequences

- Important choices are documented near the architecture docs  
- Later ADRs can supersede earlier ones without rewriting history  
- MVP implementation PRs should add ADRs for irreversible defaults (e.g. Neo4j vs Neptune)
