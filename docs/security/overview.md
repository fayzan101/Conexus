# Security Overview

## Principles

- Security by design  
- Least privilege  
- Defense in depth  
- Evidence access never bypasses ACL  
- Auditability of admin and data access  

---

## Controls

| Control | Description |
|---------|-------------|
| RBAC | Role-based access control (MVP) |
| ABAC | Attribute-based policies (Phase 2+) |
| Encryption in transit | TLS 1.2+ |
| Encryption at rest | Disk/object store & DB encryption; connector DEKs via AES-256-GCM envelope (`KMS_BACKEND=local\|vault`) |
| Audit logs | Auth, admin, search/chat access (configurable) |
| Private deployment | Single-tenant, VPC, on-prem, air-gapped options |
| SSO | Production path = OIDC (JWKS); SAML requires signature / forbids `SAML_PILOT_UNSIGNED` in prod |
| Secrets management | Vault / cloud secret manager; prod boot refuses demo `SECRET_KEY` |
| Prod profile | Forces Redis queue, real embeddings (not hash), `REQUIRE_TLS`, short-lived access tokens |
| Data retention | Configurable retention & deletion |
| Compliance support | SOC2/GDPR-oriented controls (process + product) |

---

## Threat Highlights

| Threat | Mitigation |
|--------|------------|
| Cross-tenant data leak | Strict tenant_id isolation in all stores |
| Prompt injection via docs | Treat content as untrusted; tool allowlists |
| Oversharing in answers | Retrieval-time ACL filter |
| Secret exfiltration | Redaction hooks; admin export controls |
| Supply chain | Locked deps, image scanning, signed deploys |

---

## Related Docs

- [access-control.md](access-control.md)  
- [compliance.md](compliance.md)  
- [../deployment/environments.md](../deployment/environments.md)
