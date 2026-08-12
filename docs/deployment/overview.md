# Deployment Overview

## Options

| Mode | Description |
|------|-------------|
| Cloud SaaS | Multi-tenant managed service |
| Single Tenant Cloud | Dedicated stack per customer |
| Private Cloud | Customer cloud account |
| On-Premises | Customer data center |
| Hybrid | Connectors on-prem, control plane cloud (or reverse) |
| Air-Gapped | No external network; local models & registries |

---

## MVP Reference Deploy

**Local / dev**

- Docker Compose: Postgres, Neo4j, Qdrant, Redis, MinIO, API, Web  

**Pilot / production**

- Kubernetes namespace per env (dev/stage/prod) via Terraform (`deploy/terraform`)  
- Helm chart `deploy/helm/enterprise-brain` (API, worker, web, HPA, PDB, Ingress)  
- Promote: GitHub Actions workflow `Promote` (`helm template` then ArgoCD/helm upgrade)  
- Ingress via Nginx  
- Managed Postgres optional  
- Secrets via Kubernetes secrets / Vault  
- Observability: Prometheus scrape `/metrics`, Grafana dashboard, OTEL collector  

Deploy modes (`DEPLOY_MODE`): `saas` | `single_tenant` | `private_vpc`. Record proofs with `POST /v1/ops/deploy-proofs`.

---

## Core Services

| Service | Image / unit |
|---------|----------------|
| `web` | Next.js |
| `api` | FastAPI |
| `worker` | Ingest / embedding workers |
| `postgres` | Relational DB |
| `neo4j` | Graph |
| `qdrant` | Vectors |
| `redis` | Cache/queue |
| `minio` | Object storage |

---

## Networking

- Public: HTTPS to web/API only  
- Private: DB/graph/vector not exposed  
- Egress: LLM provider (unless air-gapped)  

---

## Air-Gapped Notes

- Mirror container images & model weights  
- Disable cloud connectors or use offline import  
- Local embedding + local LLM required  
- License/offline update channel defined by ops policy  

See [environments.md](environments.md) and [../operations/runbook.md](../operations/runbook.md).
