# Technology Stack

## Frontend

| Technology | Role |
|------------|------|
| Next.js | App framework / SSR |
| React | UI components |
| TypeScript | Type safety |
| Tailwind CSS | Styling |
| Cytoscape.js | Knowledge graph visualization |

## Backend

| Technology | Role |
|------------|------|
| FastAPI (Python) | Primary API & AI orchestration |
| Node.js | Optional realtime / connector workers |
| LangGraph / LlamaIndex / LangChain | Agent & RAG orchestration (as appropriate) |

## Authentication

| Option | Typical use |
|--------|-------------|
| Keycloak | On-prem / private cloud SSO |
| Auth0 | Managed enterprise SaaS auth |
| Clerk | Fast SaaS MVP auth |

## Data Stores

| Store | Role |
|-------|------|
| PostgreSQL | Relational app data |
| Neo4j | Knowledge graph (alts: Memgraph, Amazon Neptune) |
| Qdrant | Vectors (alts: Weaviate, Milvus) |
| Redis | Cache / queues / rate limits |

## Object Storage

| Option | Role |
|--------|------|
| MinIO | S3-compatible private storage |
| Amazon S3 | Cloud object storage |

## Infrastructure

| Technology | Role |
|------------|------|
| Docker | Containerization |
| Kubernetes | Orchestration |
| Kafka | Event streaming (scale-out ingest) |
| Nginx | Ingress / reverse proxy |

## Observability

| Technology | Role |
|------------|------|
| Prometheus | Metrics |
| Grafana | Dashboards |
| OpenTelemetry | Traces & telemetry standard |

## CI/CD & IaC

| Technology | Role |
|------------|------|
| GitHub Actions | CI |
| ArgoCD | GitOps CD |
| Terraform | Infrastructure as code |

---

## Default MVP Choices

To reduce early complexity:

- **Auth:** Clerk or Keycloak (one primary)  
- **API:** FastAPI only  
- **Graph:** Neo4j  
- **Vectors:** Qdrant  
- **Queue:** Redis (Kafka later)  
- **Storage:** MinIO locally / S3 in cloud  

Rationale and swap points: keep interfaces behind repository adapters so Neo4j↔Neptune or Qdrant↔Weaviate swaps remain feasible.
