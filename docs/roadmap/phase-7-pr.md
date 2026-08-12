# Phase 7 PR — Platform Operations & Deployability

**Branch:** `phase-7-platform-ops`  
**Compare:** `phase-6-enterprise-security...phase-7-platform-ops`

## Summary

- **K8s:** Helm chart for API/worker/web with HPA, PDB, probes, resource requests/limits; Kustomize env overlays
- **IaC:** Terraform namespace + runtime ConfigMap; `dev` / `staging` / `prod` tfvars
- **Observability:** Prometheus `/metrics`, golden signals + SLO APIs, Grafana dashboard, Prometheus alerts, OTEL collector config, request-id traces
- **Reliability:** Backup/restore drill recording with RPO/RTO matrix; simulated chaos failover
- **Cost:** Per-tenant LLM daily token quota, cache hits, task-based model routing
- **Deploy matrix:** SaaS / single-tenant / private VPC proofs
- **UI:** `/ops` console for SLOs, budget, drills
- **Schema:** Alembic `0007`
- **CI:** `Promote` workflow (`helm template` + staging smoke script)

## Test plan

- [ ] `cd backend && .venv/Scripts/python.exe -m pytest -m "not integration"`
- [ ] `GET /metrics` returns Prometheus text; `GET /livez` aliases liveness
- [ ] Admin `GET /v1/ops/slo` and `/v1/ops/golden-signals`; employee receives 403
- [ ] `PUT /v1/ops/llm-budget` then chat uses stub when quota exhausted
- [ ] `POST /v1/ops/backup-drills` for postgres; listed under `/v1/ops/backup`
- [ ] `POST /v1/ops/deploy-proofs` with `single_tenant`; profile shows tested
- [ ] `POST /v1/ops/chaos/failover` records steps
- [ ] Open `/ops` as admin after login
- [ ] Optional: `helm template` via `make helm-template` or Promote workflow

## Exit criteria

- [ ] Staging≈prod Helm values exist (`values-staging.yaml` / `values-prod.yaml`)
- [ ] SLO dashboards + pageable alerts defined
- [ ] Restore drill can be recorded (API + ops UI)
- [ ] One single-tenant deploy proof can be recorded
- [ ] LLM budget enforced per tenant in tests
