# Webhooks (Phase 2)

## Purpose

Notify external systems when ingest, graph, or agent workflows complete.

## Configuration

Admins register endpoints with:

- HTTPS URL  
- Secret for HMAC signature  
- Event subscriptions  
- Optional filters (project, source_system)

## Event Types

| Event | Payload summary |
|-------|-----------------|
| `ingest.completed` | job_id, document_id, stats |
| `ingest.failed` | job_id, error |
| `meeting.processed` | meeting_id, artifacts |
| `decision.created` | decision_id |
| `freshness.alert` | entity_id, scores (Phase 2+) |
| `agent.report.ready` | report_id (Phase 3) |

## Delivery

- At-least-once delivery with retries and exponential backoff.  
- `X-EB-Signature` HMAC-SHA256 of body using shared secret.  
- `X-EB-Event`, `X-EB-Delivery-Id` headers.  
- Endpoints should respond `2xx` within timeout; otherwise retry.

## Example Payload

```json
{
  "id": "evt_123",
  "type": "ingest.completed",
  "created_at": "2026-08-05T12:00:00Z",
  "data": {
    "job_id": "job_...",
    "document_id": "doc_...",
    "nodes_upserted": 12,
    "chunks_indexed": 40
  }
}
```
