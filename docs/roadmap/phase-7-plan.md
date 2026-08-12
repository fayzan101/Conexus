# Phase 7 Plan — Platform Operations & Deployability

**Status:** Implemented on branch `phase-7-platform-ops`  
**Prerequisite:** Phase 6 enterprise security & compliance  
**Quality bar:** Unit + API tests; packaging file checks; staging smoke script (no live cluster required in CI)

## Slices

| Slice | Capability |
|-------|------------|
| Environments / IaC | Terraform namespace + runtime ConfigMap; `dev` / `staging` / `prod` tfvars |
| Kubernetes | Helm chart for API, worker, web with HPA, PDB, probes, resource requests/limits; Kustomize overlays |
| Observability | Prometheus `/metrics`, golden signals, SLO endpoint, Grafana dashboard, alert rules, OTEL collector config, request traces |
| Reliability | Backup/restore drill API + RPO/RTO matrix; simulated chaos failover |
| Cost controls | Per-tenant LLM daily token quota, response cache, task-based model routing |
| Deploy matrix | SaaS / single-tenant / private VPC proofs recorded via API |
| Promotion | GitHub Actions `Promote` workflow (`helm template` + staging smoke pointer) |

## Out of scope (Phase 8)

- Trained ML replacing heuristics
- LangGraph agents + HITL automation
- SOC2 evidence pack / GA SLA commercial terms
- Live ArgoCD install in a customer cluster (chart + workflow are the contract)
