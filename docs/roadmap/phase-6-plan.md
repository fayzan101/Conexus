# Phase 6 Plan — Enterprise Security & Compliance

**Status:** Implemented on branch `phase-6-enterprise-security`  
**Prerequisite:** Phase 5 scale & knowledge quality  
**Quality bar:** Security regression pack; ABAC matrix; retention cascade; prompt-injection suite

## Slices

| Slice | Capability |
|-------|------------|
| SSO | SAML ACS + metadata; SCIM 2.0 Users provisioning |
| ABAC | Classification / region / project membership at retrieval time + blocked reasons |
| Audit & retention | Immutable audit log export; retention job; legal hold; DSR cascade |
| Secrets | Local/Vault-shaped KMS wrap; connector credential encryption + rotate |
| Private LLM | `llm_mode=public\|private\|airgap`; no-train headers; egress guard |
| AppSec | Bandit + pip-audit in CI; prompt-injection tests |

## Out of scope (later)

- Full commercial IdP certification packs
- Hardware HSM
- Formal SOC2 audit engagement
