# Operations Runbook (Outline)

## On-Call Responsibilities

- Respond to pageable alerts for API, workers, data stores  
- Triage ingest backlog and LLM provider outages  
- Escalate security incidents per policy  

---

## Common Incidents

### API unhealthy

1. Check `/livez` (liveness) and `/readyz`  
2. Verify Postgres, Neo4j, Qdrant, Redis connectivity  
3. Inspect `GET /v1/ops/golden-signals` and `/v1/ops/slo` (pageable?)  
4. Inspect recent deploy / config change  
5. Roll back Helm release if needed  

### Ingest backlog

1. Check worker replicas and `eb_ingest_queue_depth` / golden-signals saturation  
2. Inspect poison queue / failed jobs (Admin UI)  
3. Scale workers via HPA or `helm upgrade --set worker.replicaCount`; pause connectors if necessary  

### Incorrect / leaking answers

1. Disable chat feature flag if severe  
2. Capture `request_id`, sources returned  
3. Verify ACL filters; add regression test  
4. Notify security if cross-tenant suspected  

### LLM provider outage

1. Fail gracefully with user-visible error  
2. Switch to backup provider/model if configured  
3. Queue non-interactive jobs for retry  

---

## Maintenance

- Index compaction / vector collection upgrades  
- Graph backup & restore drills  
- Certificate rotation  
- Secret rotation  
- Dependency and base image updates  

---

## Backups

| Store | Cadence (suggested) | RPO / RTO (default) |
|-------|---------------------|---------------------|
| PostgreSQL | Daily + PITR | RPO ≤ 1h / RTO 4h |
| Neo4j | Daily snapshots | RPO 24h / RTO 4h |
| Object store | Versioning + replica | RPO 24h / RTO 4h |
| Qdrant | Snapshot before reindex | RPO 24h / RTO 4h |

Record restore drills via `POST /v1/ops/backup-drills` or the `/ops` UI. Simulated failover: `POST /v1/ops/chaos/failover`.

Override with `BACKUP_RPO_HOURS` / `BACKUP_RTO_HOURS`.
