# REST API Reference (MVP Outline)

> Endpoint shapes are the intended MVP contract. Implement behind FastAPI with OpenAPI generation.

## Auth

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/auth/login` | Login (if local) / exchange |
| POST | `/v1/auth/logout` | Invalidate session |
| GET | `/v1/auth/me` | Current user + roles |

SSO may terminate at IdP; API validates JWT.

---

## Users & Roles (Admin)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/users` | List users |
| POST | `/v1/users` | Invite / create |
| PATCH | `/v1/users/{id}` | Update profile/roles |
| GET | `/v1/roles` | List roles |

---

## Documents & Ingest

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/documents` | Upload document (multipart) |
| GET | `/v1/documents` | List documents |
| GET | `/v1/documents/{id}` | Get metadata |
| DELETE | `/v1/documents/{id}` | Soft-delete / tombstone |
| POST | `/v1/meetings/transcripts` | Ingest transcript |
| GET | `/v1/jobs/{id}` | Ingest/processing job status |

---

## Search

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/search` | Semantic / hybrid search |

**Request body (example)**

```json
{
  "query": "Why was Feature X removed?",
  "filters": {
    "project_id": "uuid",
    "date_from": "2024-01-01",
    "date_to": "2025-12-31",
    "types": ["document", "meeting"]
  },
  "limit": 10
}
```

**Response (example)**

```json
{
  "results": [
    {
      "id": "chunk_...",
      "score": 0.84,
      "snippet": "...",
      "source": {
        "document_id": "uuid",
        "title": "RFC-42",
        "uri": "..."
      }
    }
  ]
}
```

---

## Chat / Assistant

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/chat/sessions` | Create session |
| POST | `/v1/chat/sessions/{id}/messages` | Send message |
| GET | `/v1/chat/sessions/{id}` | Session history |

**Message response must include** `confidence`, `sources`, optional `related_*`, `timeline`, `supporting_evidence`.

---

## Knowledge Graph

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/graph/nodes/{id}` | Node detail |
| GET | `/v1/graph/nodes/{id}/neighbors` | Adjacent nodes |
| POST | `/v1/graph/search` | Find nodes by label/property |
| POST | `/v1/graph/path` | Shortest / bounded path |

---

## Decisions (MVP)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/decisions` | List |
| POST | `/v1/decisions` | Create |
| GET | `/v1/decisions/{id}` | Detail |
| PATCH | `/v1/decisions/{id}` | Update status/fields |

---

## Dashboard Metrics

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/metrics/overview` | Ingest, docs, queries |

---

## Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/healthz` | Liveness |
| GET | `/readyz` | Readiness (DB/graph/vector) |
