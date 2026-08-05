# SDKs

Official SDKs (Phase 2+):

| Language | Package (planned) | Notes |
|----------|-------------------|-------|
| Python | `enterprise-brain` | First-class for data science & automations |
| JavaScript/TypeScript | `@enterprise-brain/sdk` | Web & Node |
| Go | `github.com/.../eb-go` | Services / CLIs |
| Java | `com.enterprisebrain:sdk` | Enterprise JVM stacks |

## Common Capabilities

- Auth (API key / OAuth token injection)  
- Documents upload & job polling  
- Search  
- Chat sessions  
- Graph node fetch  
- Typed errors and retries  

## Python Sketch

```python
from enterprise_brain import Client

client = Client(base_url="https://api.example/v1", api_key="...")

job = client.documents.upload("./spec.pdf", project_id="...")
client.jobs.wait(job.id)

hits = client.search("Who approved pricing changes?")
answer = client.chat.ask("Summarize Project Phoenix risks")
print(answer.confidence, answer.sources)
```

## Versioning

SDKs track REST major versions. Breaking API changes bump SDK major.
