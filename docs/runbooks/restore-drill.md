# Restore drill (single-tenant staging)

Evidence artifact for production hardening P3. Run against staging volumes, not production.

## Prerequisites

- Staging Compose or Helm release with Postgres, Qdrant, Neo4j, object store
- Fresh backup from `scripts/backup_all.sh`
- Operator access to restore into an isolated namespace

## Steps

1. Create backup: `BACKUP_DIR=./backups ./scripts/backup_all.sh all`
2. Record drill via API: `POST /v1/ops/backup/drill` with `{ "store": "postgres", "status": "started" }`
3. Restore Postgres dump into empty database (`pg_restore -c -d ...`)
4. Restore Qdrant snapshot to versioned collection; smoke search
5. Spot-check Neo4j neighbor query with `tenant_id` predicate
6. Fetch one object by `object_key`
7. Hit `/readyz` and `/metrics` on restored API
8. Close drill: `status=passed` with notes of measured RPO/RTO

## Exit evidence

Keep: dump checksums, restore timestamps, `/readyz` JSON, dual-replica `/metrics` scrape from two API pods.
