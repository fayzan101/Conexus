# Environments & Configuration

## Environments

| Env | Purpose |
|-----|---------|
| `local` | Developer machines |
| `dev` | Shared integration |
| `staging` | Pre-prod validation |
| `prod` | Production |

---

## Required Configuration (conceptual)

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection |
| `NEO4J_URI` / user / password | Graph DB |
| `QDRANT_URL` | Vector DB |
| `REDIS_URL` | Cache/queue |
| `OBJECT_STORE_ENDPOINT` | MinIO/S3 |
| `OBJECT_STORE_BUCKET` | Raw artifacts |
| `AUTH_PROVIDER` | keycloak \| auth0 \| clerk |
| `AUTH_*` | Provider-specific settings |
| `LLM_PROVIDER` | openai \| azure \| local |
| `LLM_API_KEY` | Secret |
| `EMBEDDING_MODEL` | Model id |
| `APP_BASE_URL` | Public URL |
| `LOG_LEVEL` | info/debug |
| `DEPLOY_MODE` | saas \| single_tenant \| private_vpc |
| `LLM_BUDGET_TOKENS_PER_DAY` | Per-tenant daily LLM token cap |
| `SLO_SEARCH_P95_MS` / `SLO_CHAT_P95_MS` | Latency budgets |
| `BACKUP_RPO_HOURS` / `BACKUP_RTO_HOURS` | DR targets |

Never commit real secrets. Use `.env.example` only with placeholders.

---

## Secrets Management

| Deploy | Recommended |
|--------|-------------|
| Local | `.env` (gitignored) |
| K8s | Sealed Secrets / External Secrets / Vault |
| Cloud | AWS Secrets Manager / GCP Secret Manager / Azure Key Vault |

---

## Feature Flags

Suggested flags:

- `ff_graphql`  
- `ff_connectors_slack`  
- `ff_research_agent`  
- `ff_ab_ac`  

Store in DB or config service per tenant where needed.
