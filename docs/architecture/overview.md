# System Architecture Overview

## High-Level Flow

```
Enterprise Systems
        ↓
Data Connectors
        ↓
Ingestion Pipeline
        ↓
AI Processing Layer
        ↓
Knowledge Graph  ←→  Vector Database
        ↓
Reasoning Engine
        ↓
AI Assistant
        ↓
Dashboards • APIs • Automation
```

---

## Logical Components

| Component | Responsibility |
|-----------|----------------|
| **Data Connectors** | Pull/push from Slack, email, Jira, GitHub, Drive, etc. |
| **Ingestion Pipeline** | Normalize, dedupe, queue, and store raw artifacts |
| **AI Processing Layer** | Parse, OCR, STT, NER, relations, topics, embeddings |
| **Knowledge Graph** | Entities, relationships, temporal & organizational structure |
| **Vector Database** | Semantic retrieval of chunks and summaries |
| **PostgreSQL** | Users, tenants, jobs, metadata, audit |
| **Redis** | Cache, rate limits, job coordination |
| **Reasoning Engine** | Retrieval planning, multi-hop graph reasoning, synthesis |
| **AI Assistant** | Chat UX and structured answer payloads |
| **API Gateway** | REST/GraphQL, authn/z, quotas |
| **Dashboards** | Ops, executive, and knowledge health UIs |
| **Automation** | Webhooks, agents, workflow suggestions (later phases) |

---

## Reference Runtime Topology (MVP)

```
                    ┌─────────────┐
                    │  Next.js UI │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   FastAPI   │
                    │  + Auth     │
                    └──┬───┬───┬──┘
           ┌───────────┘   │   └───────────┐
           ▼               ▼               ▼
     PostgreSQL         Neo4j           Qdrant
           │               │               │
           └───────┬───────┴───────┬───────┘
                   ▼               ▼
            Ingest Workers    LLM Provider
            (Kafka/Redis)     (cloud/local)
```

---

## Data Planes

| Store | Primary use |
|-------|-------------|
| PostgreSQL | Identity, RBAC, tenants, jobs, structured app data |
| Neo4j (or Memgraph / Neptune) | Knowledge graph |
| Qdrant (or Weaviate / Milvus) | Embeddings / semantic search |
| Object storage (MinIO / S3) | Raw files, transcripts, exports |
| Redis | Sessions/cache/queues (MVP may use Redis queues) |
| Kafka | High-volume event bus (Phase 2+) |

---

## Request Paths

### Search / Chat

1. Authenticate user; resolve roles and ACL filters.  
2. Plan retrieval (vector + keyword + graph expansion).  
3. Fetch evidence; filter by ACL.  
4. Reason / generate answer with citations and confidence.  
5. Log query for audit and quality feedback.

### Ingest

1. Accept upload or connector event.  
2. Persist raw object + metadata.  
3. Enqueue processing stages.  
4. Update graph nodes/edges and vector index.  
5. Emit completion event / webhook.

---

## Design Principles

- **Provenance first** — every node/chunk traces to a source.  
- **ACL at retrieval time** — never synthesize from forbidden evidence.  
- **Modular pipelines** — stages are independently scalable.  
- **Explainable outputs** — confidence, sources, related entities.  
- **Deploy anywhere** — SaaS to air-gapped with config swaps (LLM, storage, auth).

Related:

- [data-model.md](data-model.md)  
- [ai-pipeline.md](ai-pipeline.md)  
- [tech-stack.md](tech-stack.md)  
- [ai-architecture.md](ai-architecture.md)
