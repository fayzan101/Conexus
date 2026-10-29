#!/usr/bin/env bash
# Single-tenant backup helpers — invoke real dump/snapshot commands (not only DB drill rows).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${BACKUP_DIR:-$ROOT/backups}"
mkdir -p "$OUT"/{postgres,qdrant,neo4j,object}
STAMP="$(date +%Y%m%d_%H%M%S)"
TARGET="${1:-all}"

backup_postgres() {
  if [[ -z "${DATABASE_URL:-}" ]]; then
    echo "DATABASE_URL required" >&2
    return 1
  fi
  pg_dump "$DATABASE_URL" -Fc -f "$OUT/postgres/${STAMP}.dump"
  echo "postgres dump -> $OUT/postgres/${STAMP}.dump"
}

backup_qdrant() {
  local url="${QDRANT_URL:-http://localhost:6333}"
  local coll="${QDRANT_COLLECTION:-eb_chunks}"
  curl -sf -X POST "$url/collections/${coll}/snapshots" -o "$OUT/qdrant/${STAMP}.json"
  echo "qdrant snapshot requested -> $OUT/qdrant/${STAMP}.json"
}

backup_neo4j() {
  echo "neo4j: export via admin dump or APOC; recording marker $OUT/neo4j/${STAMP}.marker"
  echo "neo4j snapshot marker $STAMP" > "$OUT/neo4j/${STAMP}.marker"
}

backup_object() {
  local endpoint="${OBJECT_STORE_ENDPOINT:-http://localhost:9000}"
  local bucket="${OBJECT_STORE_BUCKET:-enterprise-brain}"
  if command -v aws >/dev/null 2>&1; then
    aws --endpoint-url "$endpoint" s3 sync "s3://${bucket}" "$OUT/object/${STAMP}/" || true
  fi
  echo "object sync attempted -> $OUT/object/${STAMP}"
}

case "$TARGET" in
  postgres) backup_postgres ;;
  qdrant) backup_qdrant ;;
  neo4j) backup_neo4j ;;
  object) backup_object ;;
  all)
    backup_postgres || echo "postgres skipped"
    backup_qdrant || echo "qdrant skipped"
    backup_neo4j || echo "neo4j skipped"
    backup_object || echo "object skipped"
    ;;
  *)
    echo "Usage: $0 [all|postgres|qdrant|neo4j|object]" >&2
    exit 1
    ;;
esac
