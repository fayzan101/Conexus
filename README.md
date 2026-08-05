# Enterprise Brain

**AI-Powered Enterprise Memory & Intelligence Platform**  
Version 1.0

Enterprise Brain transforms disconnected enterprise data into a connected knowledge graph—the organization's institutional memory. It captures knowledge, preserves decisions, maps relationships, and enables AI-driven reasoning across the company.

Employees ask natural language questions and receive trustworthy answers backed by verifiable evidence, timelines, relationships, and confidence scores.

---

## Vision

Create the world's most intelligent organizational memory system.

- Instead of storing files, Enterprise Brain stores **knowledge**.
- Instead of searching documents, users **ask questions**.
- Instead of losing experience when employees leave, the organization retains **institutional intelligence**.

## Mission

Enable every organization to instantly understand:

| Question | Capability |
|----------|------------|
| What happened? | Timeline & event reconstruction |
| Why did it happen? | Decision intelligence & evidence |
| Who knows about it? | Expertise discovery |
| What should happen next? | Recommendations & predictions |

---

## Quick Start

```bash
cp .env.example .env
cp frontend/.env.local.example frontend/.env.local

docker compose up -d postgres neo4j qdrant redis minio minio-init

cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# new terminal
cd frontend
npm install
npm run dev
```

- Web: http://localhost:3000  
- API docs: http://localhost:8000/docs  
- Dev login: `admin@enterprisebrain.local` / `admin123`

Full setup: [Local Development](docs/development/local-setup.md) · [MVP Scope](docs/roadmap/mvp.md)

### Repository layout

```
backend/     FastAPI API, ingest, RAG, graph adapters
frontend/    Next.js UI (dashboard, search, chat, graph, admin)
docs/        Product & engineering documentation
docker-compose.yml
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [Documentation Index](docs/README.md) | Full docs map |
| [Product Requirements](docs/product/prd.md) | PRD & functional requirements |
| [Architecture](docs/architecture/overview.md) | System design & components |
| [Knowledge Graph Model](docs/architecture/data-model.md) | Nodes, edges, entities |
| [API Reference](docs/api/overview.md) | REST, GraphQL, webhooks |
| [Security](docs/security/overview.md) | Auth, RBAC/ABAC, compliance |
| [Roadmap](docs/roadmap/phases.md) | MVP → Phase 3 |
| [Contributing](CONTRIBUTING.md) | Development guidelines |

---

## Platform at a Glance

```
Enterprise Systems → Data Connectors → Ingestion Pipeline
        → AI Processing → Knowledge Graph + Vector DB
        → Reasoning Engine → AI Assistant
        → Dashboards • APIs • Automation
```

### Core Modules

1. Enterprise Knowledge Graph  
2. Meeting Memory  
3. Decision Intelligence  
4. Company Timeline  
5. Project Memory  
6. Expertise Discovery  
7. Knowledge Freshness  
8. Business Dependency Graph  
9. Enterprise Search  
10. AI Research Agent  
11. Opportunity Discovery  
12. Workflow Intelligence  
13. Predictive Analytics  
14. Enterprise AI Assistant  
15. Executive Dashboard  

Details: [Functional Modules](docs/modules/overview.md)

---

## Technology Stack

| Layer | Technologies |
|-------|----------------|
| Frontend | Next.js, React, TypeScript, Tailwind CSS, Cytoscape.js |
| Backend | FastAPI, Python, Node.js |
| Auth | Keycloak / Auth0 / Clerk |
| Data | PostgreSQL, Neo4j, Qdrant, Redis |
| Storage | MinIO / Amazon S3 |
| Infra | Docker, Kubernetes, Kafka, Nginx |
| Observability | Prometheus, Grafana, OpenTelemetry |
| CI/CD | GitHub Actions, ArgoCD, Terraform |

---

## Deployment Options

- Cloud SaaS  
- Single-tenant cloud  
- Private cloud  
- On-premises  
- Hybrid  
- Air-gapped  

---

## License

Proprietary — see [LICENSE](LICENSE). All rights reserved.
