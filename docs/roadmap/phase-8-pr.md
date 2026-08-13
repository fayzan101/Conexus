# Phase 8 PR — GA / Production Maturity

**Branch:** `phase-8-ga-maturity`  
**Compare:** `phase-7-platform-ops...phase-8-ga-maturity`

## Summary

- **ML:** Calibrated risk models + offline evals; expert feedback ranking; forecast backtesting
- **Agents:** Tool allowlists, HITL write approvals, agent eval harness
- **Automation:** Policy-gated notify / ticket / doc-draft actions
- **Executive:** Locked KPIs, trends, board packs, role views
- **Quality:** Continuous RAG/agent/perf eval gates; public `/v1/status` + `/status` UI
- **Compliance:** SOC2 evidence pack, GDPR DPA/data map, pen-test remediation tracking
- **Commercial:** Billing plans/quotas; SLA uptime measurements
- **Schema:** Alembic `0008`
- **UI:** `/ga` console, `/status` page

## Test plan

- [ ] `cd backend && .venv/Scripts/python.exe -m pytest -m "not integration"`
- [ ] `POST /v1/ml/evals/run` all models `passed`
- [ ] `POST /v1/agents/run` with `draft_doc` → approval → decide approve
- [ ] Blocked automation without `approval_token` for write patterns
- [ ] `GET /v1/executive/board-pack` returns locked KPIs
- [ ] `POST /v1/evals/run` green with recall/citation above thresholds
- [ ] Pen-test open finding flips GA readiness false until closed
- [ ] `PUT /v1/billing/plan` + `POST /v1/sla/measurements`
- [ ] Public `GET /v1/status` and `/status` page load without auth

## Exit criteria (= 100% production maturity bar in-product)

- [ ] GA version `1.0.0` surfaced on status/readiness  
- [ ] Eval gates enforceable in CI  
- [ ] Compliance pack + pen-test closure path  
- [ ] SLA + billing quotas available to admins  
- [ ] Agent writes require HITL  
