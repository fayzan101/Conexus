# Contributing

Thanks for contributing to Enterprise Brain (Cognexus).

## Before You Start

1. Read [docs/README.md](docs/README.md) and the [MVP scope](docs/roadmap/mvp.md).  
2. Align changes with [product principles](docs/product/vision.md).  
3. For features outside MVP, note the target phase in the PR.  

## Development Setup

See [docs/development/local-setup.md](docs/development/local-setup.md).

## Workflow

1. Create a branch: `feat/…`, `fix/…`, `docs/…`  
2. Keep PRs focused and reviewable  
3. Include tests for API/ACL/retrieval changes  
4. Update docs when behavior or APIs change  
5. Ensure CI passes  

### Phase delivery branches

Each product phase lands on its **own branch** and ends with a **pull request + description**:

| Phase | Branch naming | When |
|-------|---------------|------|
| Phase 1 Foundation | `phase-1-foundation` | After MVP slices A–E |
| Phase 2 Knowledge Layer | `phase-2-enterprise-intelligence` | After Phase 2 slices |
| Phase 3 AI OS | `phase-3-ai-operating-system` | After Phase 3 slices |

Do not mix multiple phases in one PR. When phase work finishes, open the PR with Summary + Test plan (see existing Phase PRs for format).

## Commit Messages

Prefer concise, imperative subjects focused on why:

```
Add ACL filtering to chat retrieval

Prevent unauthorized chunks from reaching the LLM context.
```

## Code Standards

Follow [docs/development/coding-standards.md](docs/development/coding-standards.md).

## Security

- Never commit secrets or production data  
- ACL and tenant isolation changes require tests  
- Report vulnerabilities privately to the maintainers  

## License

By contributing, you agree that contributions are proprietary to the project owners under the [LICENSE](LICENSE).
