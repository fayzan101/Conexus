# AI Architecture

## Language Models

| Model class | Use |
|-------------|-----|
| GPT-5.5 (or current frontier reasoning model) | Complex reasoning, research agent, executive reports |
| Optional local models | Privacy-sensitive / air-gapped deployments |

Model selection must be configurable per tenant and environment.

---

## Embeddings

| Option | Use |
|--------|------|
| Sentence Transformers | Default / private deployments |
| OpenAI Embeddings | Optional cloud quality/latency tradeoff |

Embedding model version is stored with each vector collection for safe reindex.

---

## Orchestration Frameworks

| Framework | When to use |
|-----------|-------------|
| LangGraph | Multi-step agents, stateful research workflows |
| LlamaIndex | Indexing, retrieval abstractions over docs/graph |
| LangChain | Lightweight chains/tools where appropriate |

Prefer a thin internal “Reasoning Engine” API so frameworks are implementation details.

---

## Knowledge Graph Engines

Supported targets: **Neo4j**, **Memgraph**, **Amazon Neptune**.

---

## Vector Databases

Supported targets: **Qdrant**, **Weaviate**, **Milvus**.

---

## Machine Learning Capabilities

| Capability | Phase | Notes |
|------------|-------|-------|
| Risk prediction | 3 | Project delay, churn, overload |
| Recommendation | 2–3 | Experts, docs, automations |
| Clustering | 2 | Topics, duplicate clusters |
| Anomaly detection | 3 | Process / access / ops anomalies |
| Forecasting | 3 | Capacity, knowledge decay |
| Graph embeddings | 2–3 | Link prediction features |
| Community detection | 2–3 | Teams / topic communities |
| Link prediction | 2–3 | Suggested relationships |

---

## Answer Contract

Every assistant response should include:

| Field | Description |
|-------|-------------|
| `answer` | Natural language response |
| `confidence` | Calibrated score 0–1 |
| `sources` | Cited chunks / URLs |
| `related_documents` | Linked docs |
| `related_projects` | Linked projects |
| `people_involved` | Employees / experts |
| `timeline` | Ordered events when relevant |
| `supporting_evidence` | Graph paths / quotes |

---

## Safety & Grounding

- Prefer grounded generation; refuse or hedge when evidence is insufficient.  
- Never use unauthorized chunks.  
- Log prompts/responses per retention policy (with redaction options).  
- Support evaluation sets for retrieval hit-rate and answer faithfulness.
