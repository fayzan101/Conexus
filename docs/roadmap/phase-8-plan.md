# Phase 8 Plan — GA / Production Maturity (100%)

**Status:** Implemented on branch `phase-8-ga-maturity`  
**Prerequisite:** Phase 7 platform operations  
**Quality bar:** Unit + API tests; continuous RAG/agent/perf eval gates; compliance pack readiness

## Slices

| Slice | Capability |
|-------|------------|
| ML maturity | Calibrated delay / knowledge-loss / overload logistics; expert ranking with labeled feedback; query-volume forecast + backtest; offline eval runs |
| Agents | Allowlisted research/ops tools; HITL approvals for write actions; agent eval harness (success, citations, unsafe rate) |
| Automation | Policy-gated `notify` / `create_ticket` / `update_doc_draft` (+ optional webhook) |
| Executive | Locked KPI definitions, snapshots/trends, board pack, role-based executive vs operator views |
| Quality / GA | Continuous eval gates API + CI job; public status page; performance budgets via SLO samples |
| Compliance | SOC2 control evidence pack, GDPR data map + DPA template, pen-test finding lifecycle |
| Commercial | Tenant billing plans/quotas; SLA definition + period measurements |

## Out of scope (post-GA)

- Full SOC2 certification engagement
- Training large production ML models on customer corpora
- Expanding connector catalog beyond priority set
