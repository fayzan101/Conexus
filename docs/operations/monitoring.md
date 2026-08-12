# Monitoring & Observability

## Stack

- **Prometheus** — scrape `GET /metrics` (in-process exposition; Helm annotates API pods)
- **Grafana** — import [deploy/observability/grafana-dashboard.json](../../deploy/observability/grafana-dashboard.json)
- **Alertmanager** — rules in [deploy/observability/prometheus-alerts.yaml](../../deploy/observability/prometheus-alerts.yaml)
- **OpenTelemetry** — collector config [deploy/observability/otel-collector.yaml](../../deploy/observability/otel-collector.yaml); API records in-process spans at `GET /v1/ops/traces`

Live SLO snapshot: `GET /v1/ops/slo` (admin). Golden signals: `GET /v1/ops/golden-signals`.

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
- SLO budget burn (`SearchLatencyBudgetBurn`, `ApiErrorRateHigh`)  
- LLM quota blocked spike  

Ops console: `/ops` (admin). Prometheus: `/metrics`.

See also [runbook.md](runbook.md).
