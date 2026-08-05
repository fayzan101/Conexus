# ADR 0002: Default Data Plane for MVP

## Status

Accepted

## Context

The platform must support multiple graph and vector backends long-term, but MVP needs a single default to ship quickly.

## Decision

MVP defaults:

| Concern | Choice |
|---------|--------|
| Relational | PostgreSQL |
| Graph | Neo4j |
| Vectors | Qdrant |
| Object storage | MinIO (local) / S3 (cloud) |
| Queue | Redis (Kafka deferred to scale-out) |
| API | FastAPI |
| Web | Next.js |

Hide stores behind repository/adapter interfaces so Neptune/Weaviate/etc. remain feasible.

## Consequences

- Faster MVP path with mature local tooling  
- Some rework if a pilot mandates Neptune-only  
- Adapter discipline required from the first schemas
