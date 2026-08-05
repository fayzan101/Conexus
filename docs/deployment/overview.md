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

**Pilot**

- Kubernetes namespace per env (dev/stage/prod)  
- Ingress via Nginx  
- Managed Postgres optional  
- Secrets via Kubernetes secrets / Vault  

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
