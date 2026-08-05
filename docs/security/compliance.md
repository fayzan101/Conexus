# Compliance, Retention & Audit

## Audit Logs

Record at minimum:

- Authentication events  
- Admin configuration changes  
- User/role changes  
- Document upload/delete  
- Connector connect/disconnect  
- Export / bulk download  
- (Optional) search/chat queries — subject to privacy policy  

Each entry: actor, action, resource, timestamp, request_id, IP/user-agent when available.

---

## Data Retention

| Data class | Default guidance |
|------------|------------------|
| Raw files | Tenant-configurable; support legal hold |
| Chunks / embeddings | Deleted with source or on policy |
| Graph entities | Soft-delete then purge |
| Chat logs | Configurable; shorter default |
| Audit logs | Longer retention (e.g. 1 year+) |

Deletion must cascade across Postgres, object store, graph, and vectors.

---

## Privacy

- Tenant isolation  
- Optional local/private LLM path  
- PII handling policies per region  
- DSR (data subject request) workflows for enterprise customers  

---

## Compliance Support

Product and process aim to support:

- GDPR-oriented data subject rights  
- SOC 2 control mapping (access, change mgmt, logging)  
- Customer DPAs for SaaS  

Exact certifications are organizational milestones, not implied by this document alone.

---

## Encryption

- TLS in transit  
- Encrypted volumes / SSE for object storage  
- Secrets never stored in plaintext config  
- Key management via cloud KMS or on-prem HSM/vault as required
