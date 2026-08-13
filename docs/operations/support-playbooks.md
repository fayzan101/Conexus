# Support Playbooks (GA)

## Severity

| Sev | Meaning | Response |
|-----|---------|----------|
| SEV1 | Cross-tenant leak, auth bypass, data loss | Page on-call; disable chat/search flags if needed |
| SEV2 | SLO burn (search/chat/error budget) | Investigate golden signals; scale or rollback |
| SEV3 | Single-tenant connector/ingest failure | Admin DLQ retry; pause connector |
| SEV4 | UI polish / non-blocking defects | Ticket backlog |

## Common playbooks

### Chat answers without citations

1. Capture `request_id` from response headers  
2. Check `/v1/ops/golden-signals` grounded ratio  
3. Re-run `POST /v1/evals/run`  
4. Add gold-set fixture if regression  

### Agent proposed unsafe write

1. Confirm allowlist in `AGENT_ALLOWLIST`  
2. Ensure `AGENT_REQUIRE_HITL_WRITES=true`  
3. Reject pending approval in `/v1/agents/approvals`  
4. File pen-test/finding if bypass observed  

### SLA breach month

1. Pull `/v1/sla` definition and latest `/v1/sla/measurements`  
2. Correlate with Prometheus alerts  
3. Customer comms via status page (`/status`)  
4. Record accepted risk or remediation in compliance pack  

See also [runbook.md](runbook.md) and [monitoring.md](monitoring.md).
