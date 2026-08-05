# Monitoring & Observability

## Stack

- **Prometheus** — metrics scrape  
- **Grafana** — dashboards & alerts  
- **OpenTelemetry** — traces across API, workers, LLM calls  

---

## Golden Signals

| Signal | Examples |
|--------|----------|
| Latency | Search P95, chat TTFB, ingest job duration |
| Traffic | QPS search/chat, ingest rate |
| Errors | 5xx rate, worker failures, LLM errors |
| Saturation | Queue depth, CPU/mem, disk, vector index size |

---

## Domain Metrics

- Documents indexed / day  
- Graph nodes/edges created  
- Embedding backlog  
- Chat grounded ratio (% answers with ≥1 source)  
- ACL filter drop rate  
- User thumbs-up/down on answers  

---

## Logging

- Structured JSON logs  
- `request_id` / `trace_id` correlation  
- No raw secrets; redact PII where required  

---

## Alerting (initial)

- API error rate spike  
- Worker queue lag  
- Neo4j / Qdrant / Postgres down  
- Object store failures  
- Certificate expiry  

See also [runbook.md](runbook.md).
