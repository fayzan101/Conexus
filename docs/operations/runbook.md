# Operations Runbook (Outline)

## On-Call Responsibilities

- Respond to pageable alerts for API, workers, data stores  
- Triage ingest backlog and LLM provider outages  
- Escalate security incidents per policy  

---

## Common Incidents

### API unhealthy

1. Check `/healthz` and `/readyz`  
2. Verify Postgres, Neo4j, Qdrant, Redis connectivity  
3. Inspect recent deploy / config change  
4. Roll back if needed  

### Ingest backlog

1. Check worker replicas and queue depth  
2. Inspect poison queue / failed jobs  
3. Scale workers; pause connectors if necessary  

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

| Store | Cadence (suggested) |
|-------|---------------------|
| PostgreSQL | Daily + PITR |
| Neo4j | Daily snapshots |
| Object store | Versioning + cross-region/replica as required |
| Qdrant | Snapshot before reindex |

Document restore RTOs/RPOs per customer tier.
