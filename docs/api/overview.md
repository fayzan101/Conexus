# API Overview

Enterprise Brain exposes **REST** (MVP), **GraphQL** (Phase 2), **Webhooks** (Phase 2), and language **SDKs**.

Base URL (example): `https://{tenant}.api.enterprisebrain.example/v1`

All authenticated requests require `Authorization: Bearer <token>` unless using session cookies from the web app.

---

## Surfaces

| Surface | Status | Doc |
|---------|--------|-----|
| REST | MVP | [rest.md](rest.md) |
| GraphQL | Phase 2 | [graphql.md](graphql.md) |
| Webhooks | Phase 2 | [webhooks.md](webhooks.md) |
| SDKs | Phase 2+ | [sdks.md](sdks.md) |

---

## Cross-Cutting Conventions

### Errors

```json
{
  "error": {
    "code": "forbidden",
    "message": "Not allowed to access this resource",
    "request_id": "req_..."
  }
}
```

### Pagination

Cursor-based: `?cursor=&limit=50` → `{ "items": [], "next_cursor": "..." }`

### Idempotency

`Idempotency-Key` header on ingest and write endpoints.

### Tenancy

Tenant resolved from token claims; never accepted solely from client body.

### Versioning

URL version `/v1`. Breaking changes require `/v2` or compatibility window documented in CHANGELOG.

---

## OpenAPI

MVP ships OpenAPI 3.x from FastAPI at `/openapi.json` and interactive docs at `/docs` (non-production may disable).
