# Coding Standards

## General

- Prefer clarity over cleverness  
- Match existing patterns once code exists  
- Keep PRs scoped; avoid drive-by refactors  
- Document public APIs and non-obvious invariants  

## TypeScript / React (Frontend)

- TypeScript strict mode  
- Next.js App Router conventions (unless repo decides otherwise)  
- Tailwind for styling; shared design tokens via CSS variables  
- Accessible interactive elements (labels, focus states)  

## Python (Backend)

- Type hints on public functions  
- FastAPI routers by domain (`auth`, `documents`, `search`, `chat`, `graph`)  
- Pydantic models for request/response  
- No unbounded graph queries; always limit depth/size  
- Structured logging with `request_id`  

## Data & ACL

- Every query scoped by `tenant_id`  
- Retrieval paths must apply ACL before generation  
- Migrations for Postgres; versioned graph migrations/constraints  

## Testing

| Layer | Expectation |
|-------|-------------|
| Unit | Pure logic, scorers, parsers |
| Integration | API + DB/graph/vector testcontainers or Compose |
| Security | ACL regression fixtures |
| Eval (later) | Retrieval/answer quality gold sets |

## Docs

- Update OpenAPI via code  
- Update `docs/api/*` for contract changes  
- Update module/roadmap docs when scope shifts
