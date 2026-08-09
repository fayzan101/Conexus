# Phase 6 PR — Enterprise Security & Compliance

**Branch:** `phase-6-enterprise-security`  
**Compare:** `phase-5-scale-quality...phase-6-enterprise-security`

## Summary

- **SSO:** SAML metadata/login/ACS + SCIM 2.0 Users (create/list/patch/deactivate)
- **ABAC:** Classification, region, project membership, principals at retrieval; `blocked_reason` / `acl_summary` on search & chat
- **Audit & retention:** Immutable audit export, legal holds, retention policies/jobs, DSR cascade delete
- **Secrets:** Local/Vault-shaped KMS wrap, tenant key + connector credential rotation
- **Private LLM:** `LLM_MODE` + egress guard + no-train headers; prompt-injection detector
- **AppSec:** Bandit + pip-audit CI job
- **Schema:** Alembic `0006`

## Test plan

- [ ] `cd backend && .venv/Scripts/python.exe -m pytest -m "not integration"`
- [ ] Upload confidential doc; user with `clearance=public` gets blocked_reason in chat
- [ ] SCIM create with `SCIM_BEARER_TOKEN`
- [ ] Legal hold blocks retention purge
- [ ] `/v1/security/audit/export` returns append-only events

## Exit criteria

- [ ] SSO + SCIM paths available  
- [ ] ABAC enforced on search/chat  
- [ ] Retention/DSR cascade covered by tests  
- [ ] Security CI job green (Bandit)
