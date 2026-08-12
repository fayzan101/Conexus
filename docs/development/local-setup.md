# Local Development Setup

## Prerequisites

- Git  
- Docker + Docker Compose  
- Node.js 20+  
- Python 3.11+  

## Quick Start

```bash
git clone <repository-url>
cd Cognexus
cp .env.example .env
cp frontend/.env.local.example frontend/.env.local

# Infrastructure
docker compose up -d postgres neo4j qdrant redis minio minio-init

# Backend
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Or use Make (Git Bash / WSL / Unix):

```bash
make up
make install
make api
# other terminal
make web
```

- Web: http://localhost:3000  
- API docs: http://localhost:8000/docs  
- Neo4j browser: http://localhost:7474  
- MinIO console: http://localhost:9001  

## Dev login

| User | Email | Password | Role |
|------|-------|----------|------|
| Admin | admin@enterprisebrain.local | admin123 | admin |
| Employee | user@enterprisebrain.local | user123 | employee |

`AUTH_PROVIDER=dev` enables local JWT auth. Swap to Clerk/Keycloak/Auth0 later.

## Services

| Service | Default port |
|---------|--------------|
| Web | 3000 |
| API | 8000 |
| Postgres | 5432 |
| Neo4j | 7474 / 7687 |
| Qdrant | 6333 |
| Redis | 6379 |
| MinIO | 9000 / 9001 |

## Useful Checks

```bash
curl http://localhost:8000/healthz
curl http://localhost:8000/livez
curl http://localhost:8000/metrics
```

Ops console (admin): http://localhost:3000/ops  
Helm chart: `deploy/helm/enterprise-brain`  
Staging smoke: `python backend/scripts/staging_smoke.py`

## Troubleshooting

- **Ready check fails:** ensure Compose services are healthy (`docker compose ps`).  
- **Auth errors:** verify `AUTH_PROVIDER=dev` and seed users exist (created on API startup).  
- **Empty search:** upload a text document or transcript first; confirm Qdrant is up.  
- **MinIO errors on upload:** metadata/text still ingest; object store is best-effort in MVP.
