"""SOC2-oriented evidence pack, GDPR data map, pen-test remediation tracking."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.models import ComplianceControl, PenTestFinding

SOC2_SEED = [
    ("CC6.1", "Logical access controls", "RBAC/ABAC on search/chat; SSO/SCIM", "security"),
    ("CC6.6", "Encryption", "TLS flag + tenant envelope keys + credential wrap", "security"),
    ("CC7.2", "System monitoring", "Prometheus metrics, SLO alerts, audit export", "ops"),
    ("CC8.1", "Change management", "Phase branches, CI, Promote workflow", "engineering"),
]

GDPR_DATA_MAP = [
    {"system": "postgres", "data": "users, documents, chat, audit, billing", "lawful_basis": "contract"},
    {"system": "neo4j", "data": "knowledge graph entities/relationships", "lawful_basis": "contract"},
    {"system": "qdrant", "data": "document chunk embeddings", "lawful_basis": "contract"},
    {"system": "object_store", "data": "raw uploaded files", "lawful_basis": "contract"},
    {"system": "llm_provider", "data": "prompts + retrieved evidence snippets", "lawful_basis": "contract"},
]

DPA_TEMPLATE = {
    "title": "Enterprise Brain Data Processing Addendum (template)",
    "version": "1.0.0",
    "roles": {"controller": "Customer", "processor": "Enterprise Brain operator"},
    "subprocessors": ["Cloud LLM provider (if public mode)", "Object storage", "IdP"],
    "retention": "Per retention_policies / RETENTION_DAYS_DEFAULT; legal hold honored",
    "dsr": "DSR cascade delete via /v1/security DSR endpoints",
    "transfers": "Private/airgap LLM mode available; document region ABAC",
}


def seed_compliance_pack(db: Session) -> list[ComplianceControl]:
    """Seed controls as partial until hardening evidence flags are set."""
    created = []
    for control_id, title, evidence, owner in SOC2_SEED:
        existing = (
            db.query(ComplianceControl)
            .filter(ComplianceControl.framework == "soc2", ComplianceControl.control_id == control_id)
            .first()
        )
        if existing:
            # Do not auto-promote to implemented without evidence
            if existing.status == "implemented" and "evidence:" not in (existing.evidence or ""):
                existing.status = "partial"
            created.append(existing)
            continue
        row = ComplianceControl(
            framework="soc2",
            control_id=control_id,
            title=title,
            status="partial",
            evidence=evidence,
            owner=owner,
        )
        db.add(row)
        created.append(row)

    gdpr = (
        db.query(ComplianceControl)
        .filter(ComplianceControl.framework == "gdpr", ComplianceControl.control_id == "DATA_MAP")
        .first()
    )
    if not gdpr:
        gdpr = ComplianceControl(
            framework="gdpr",
            control_id="DATA_MAP",
            title="Personal data map",
            status="partial",
            evidence=str(GDPR_DATA_MAP),
            owner="compliance",
        )
        db.add(gdpr)
        created.append(gdpr)
    else:
        created.append(gdpr)

    db.commit()
    for r in created:
        db.refresh(r)
    return created


def hardening_gates(settings: Settings | None = None) -> dict[str, bool]:
    cfg = settings or get_settings()
    return {
        "trust_hardening_complete": bool(cfg.trust_hardening_complete),
        "isolation_hardening_complete": bool(cfg.isolation_hardening_complete),
        "encryption_at_rest_verified": bool(cfg.encryption_at_rest_verified),
        "require_tls": bool(cfg.require_tls),
        "non_hash_embeddings": (cfg.embedding_provider or "").lower() != "hash" or not cfg.is_prod_like,
        "oidc_or_saml": cfg.auth_provider in {"oidc", "saml"} or not cfg.is_prod_like,
    }


def compliance_pack(db: Session, settings: Settings | None = None) -> dict:
    cfg = settings or get_settings()
    seed_compliance_pack(db)
    controls = db.query(ComplianceControl).order_by(ComplianceControl.framework, ComplianceControl.control_id).all()
    findings = db.query(PenTestFinding).order_by(PenTestFinding.created_at.desc()).all()
    open_findings = [f for f in findings if f.status == "open"]
    gates = hardening_gates(cfg)
    gates_ok = all(
        [
            gates["trust_hardening_complete"],
            gates["isolation_hardening_complete"],
            len(open_findings) == 0,
        ]
    )
    return {
        "soc2_controls": [
            {
                "control_id": c.control_id,
                "title": c.title,
                "status": c.status,
                "evidence": c.evidence,
                "owner": c.owner,
            }
            for c in controls
            if c.framework == "soc2"
        ],
        "gdpr": {
            "data_map": GDPR_DATA_MAP,
            "dpa_template": DPA_TEMPLATE,
        },
        "pentest": {
            "total": len(findings),
            "open": len(open_findings),
            "closed_or_accepted": len(findings) - len(open_findings),
            "findings": [
                {
                    "id": str(f.id),
                    "title": f.title,
                    "severity": f.severity,
                    "status": f.status,
                    "owner": f.owner,
                    "remediation": f.remediation,
                }
                for f in findings
            ],
        },
        "hardening_gates": gates,
        "ready_for_ga": gates_ok and len(open_findings) == 0,
    }


def upsert_pentest_finding(
    db: Session,
    *,
    title: str,
    severity: str = "medium",
    owner: str | None = None,
    remediation: str | None = None,
    status: str = "open",
) -> PenTestFinding:
    row = PenTestFinding(
        title=title,
        severity=severity,
        status=status,
        owner=owner,
        remediation=remediation,
        closed_at=datetime.now(timezone.utc) if status in {"remediated", "accepted"} else None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def close_pentest_finding(
    db: Session,
    finding_id: UUID,
    *,
    status: str = "remediated",
    remediation: str | None = None,
) -> PenTestFinding:
    row = db.get(PenTestFinding, finding_id)
    if not row:
        raise ValueError("Finding not found")
    if status not in {"remediated", "accepted"}:
        raise ValueError("status must be remediated or accepted")
    row.status = status
    if remediation:
        row.remediation = remediation
    row.closed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row
