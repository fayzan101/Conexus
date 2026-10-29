"""Backup/restore drill recording and documented RPO/RTO per store."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import BackupDrill, ChaosTest, DeployProof

STORES = ("postgres", "neo4j", "qdrant", "object")
DEPLOY_MODES = ("saas", "single_tenant", "private_vpc")


def rpo_rto_matrix(settings: Settings) -> dict:
    return {
        "postgres": {
            "cadence": "daily + PITR",
            "rpo_hours": min(1.0, settings.backup_rpo_hours),
            "rto_hours": settings.backup_rto_hours,
        },
        "neo4j": {
            "cadence": "daily snapshots",
            "rpo_hours": settings.backup_rpo_hours,
            "rto_hours": settings.backup_rto_hours,
        },
        "qdrant": {
            "cadence": "snapshot before reindex",
            "rpo_hours": settings.backup_rpo_hours,
            "rto_hours": settings.backup_rto_hours,
        },
        "object": {
            "cadence": "versioning + replica",
            "rpo_hours": settings.backup_rpo_hours,
            "rto_hours": settings.backup_rto_hours,
        },
    }


def restore_checklist(store: str) -> list[str]:
    store = store.lower()
    common = [
        "Confirm backup artifact exists and checksum matches",
        "Restore into isolated namespace / volume",
        "Run /readyz against restored stack",
        "Record RPO (data lag) and RTO (elapsed restore)",
    ]
    extra = {
        "postgres": ["pg_basebackup / PITR to agreed timestamp", "Verify tenant_id rows present"],
        "neo4j": ["Load dump into empty store", "Spot-check graph neighbor query"],
        "qdrant": ["Restore snapshot to versioned collection", "Search recall smoke query"],
        "object": ["Restore bucket prefix", "Fetch one document object_key"],
    }
    return extra.get(store, []) + common


def record_drill(
    db: Session,
    settings: Settings,
    *,
    store: str,
    environment: str | None = None,
    status: str = "passed",
    notes: str | None = None,
    performed_by: UUID | None = None,
    tenant_id: str | None = None,
) -> BackupDrill:
    store = store.lower()
    if store not in STORES:
        raise ValueError(f"Unknown store '{store}'; expected one of {STORES}")
    matrix = rpo_rto_matrix(settings)[store]
    row = BackupDrill(
        tenant_id=tenant_id or settings.default_tenant_id,
        environment=environment or settings.environment,
        store=store,
        rpo_hours=matrix["rpo_hours"],
        rto_hours=matrix["rto_hours"],
        status=status,
        notes=notes,
        performed_by=performed_by,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_drills(db: Session, *, tenant_id: str | None = None, limit: int = 50) -> list[BackupDrill]:
    q = db.query(BackupDrill).order_by(BackupDrill.performed_at.desc())
    if tenant_id:
        q = q.filter(BackupDrill.tenant_id == tenant_id)
    return q.limit(limit).all()


def record_deploy_proof(
    db: Session,
    *,
    deploy_mode: str,
    environment: str,
    notes: str | None = None,
    proven_by: UUID | None = None,
    status: str = "proven",
) -> DeployProof:
    mode = deploy_mode.lower().replace("-", "_")
    if mode not in DEPLOY_MODES:
        raise ValueError(f"Unknown deploy_mode '{deploy_mode}'; expected one of {DEPLOY_MODES}")
    row = DeployProof(
        deploy_mode=mode,
        environment=environment,
        status=status,
        notes=notes,
        proven_by=proven_by,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def deploy_matrix(db: Session, settings: Settings) -> dict:
    proofs = db.query(DeployProof).order_by(DeployProof.proven_at.desc()).all()
    latest: dict[str, DeployProof] = {}
    for p in proofs:
        latest.setdefault(p.deploy_mode, p)
    modes = {}
    for mode in DEPLOY_MODES:
        p = latest.get(mode)
        modes[mode] = {
            "tested": p is not None and p.status == "proven",
            "environment": p.environment if p else None,
            "proven_at": p.proven_at.isoformat() if p and p.proven_at else None,
            "notes": p.notes if p else None,
            "active": settings.deploy_mode == mode,
        }
    return {
        "environment": settings.environment,
        "deploy_mode": settings.deploy_mode,
        "modes": modes,
    }


def simulate_failover(
    db: Session,
    settings: Settings,
    *,
    component: str,
    environment: str | None = None,
    performed_by: UUID | None = None,
) -> ChaosTest:
    component = (component or "api").lower()
    steps = [
        f"Mark {component} replica unready (PDB keeps remaining pods)",
        "Confirm /readyz fails on drained replica and succeeds on remaining",
        "Confirm ingest queue drains on surviving worker",
        "Restore replica; HPA/PDB back to desired",
    ]
    row = ChaosTest(
        component=component,
        environment=environment or settings.environment,
        status="passed",
        steps=steps,
        notes="Simulated game-day failover (no live kill in this environment).",
        performed_by=performed_by,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_chaos(db: Session, *, limit: int = 20) -> list[ChaosTest]:
    return db.query(ChaosTest).order_by(ChaosTest.performed_at.desc()).limit(limit).all()


def backup_command_matrix(settings: Settings) -> dict[str, list[str]]:
    """Documented/invokable backup commands for single-tenant DR (not just drill rows)."""
    db_url = settings.database_url
    return {
        "postgres": [
            "pg_dump \"$DATABASE_URL\" -Fc -f backups/postgres/$(date +%Y%m%d).dump",
            f"# DATABASE_URL={db_url.split('@')[-1] if '@' in db_url else '(set locally)'}",
        ],
        "qdrant": [
            "curl -X POST \"$QDRANT_URL/collections/$QDRANT_COLLECTION/snapshots\"",
            "scripts/backup_all.sh qdrant",
        ],
        "neo4j": [
            "cypher-shell -u $NEO4J_USER -p $NEO4J_PASSWORD 'CALL apoc.export.cypher.all(\"backup.cypher\", {})'",
            "scripts/backup_all.sh neo4j",
        ],
        "object": [
            "aws --endpoint-url $OBJECT_STORE_ENDPOINT s3 sync s3://$OBJECT_STORE_BUCKET backups/object/",
            "scripts/backup_all.sh object",
        ],
    }
