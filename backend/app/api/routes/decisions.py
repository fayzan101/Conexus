from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.db.models import Decision, DecisionLink, DecisionStatus
from app.deps import AppSettings, CurrentUser, DbSession
from app.schemas import (
    DecisionCreate,
    DecisionLinkCreate,
    DecisionLinkOut,
    DecisionOut,
    DecisionUpdate,
)
from app.services.graph import GraphStore

router = APIRouter(prefix="/v1/decisions", tags=["decisions"])


@router.get("", response_model=list[DecisionOut])
def list_decisions(db: DbSession, _: CurrentUser):
    return db.query(Decision).order_by(Decision.created_at.desc()).limit(100).all()


@router.post("", response_model=DecisionOut, status_code=status.HTTP_201_CREATED)
def create_decision(payload: DecisionCreate, db: DbSession, settings: AppSettings, _: CurrentUser):
    data = payload.model_dump()
    links = data.pop("links", None) or []
    decision = Decision(**{k: v for k, v in data.items() if k != "links"})
    db.add(decision)
    db.flush()
    for link in links:
        db.add(
            DecisionLink(
                decision_id=decision.id,
                link_type=link["link_type"],
                target_id=link["target_id"],
                target_title=link.get("target_title"),
                source_system=link.get("source_system"),
            )
        )
    if decision.supersedes_id:
        old = db.get(Decision, decision.supersedes_id)
        if old:
            old.status = DecisionStatus.superseded
    db.commit()
    db.refresh(decision)

    try:
        graph = GraphStore(settings)
        graph.upsert_node(
            "Decision",
            str(decision.id),
            {"title": decision.title, "status": decision.status.value},
        )
        if decision.project_id:
            graph.upsert_edge(
                "Decision", str(decision.id), "Project", str(decision.project_id), "BELONGS_TO"
            )
        if decision.approver_id:
            graph.upsert_edge(
                "Decision",
                str(decision.id),
                "Employee",
                str(decision.approver_id),
                "APPROVED_BY",
            )
        if decision.supersedes_id:
            graph.upsert_edge(
                "Decision",
                str(decision.id),
                "Decision",
                str(decision.supersedes_id),
                "SUPERSEDES",
            )
        graph.close()
    except Exception:
        pass
    return decision


@router.get("/query/who-approved")
def who_approved(db: DbSession, _: CurrentUser, q: str):
    rows = (
        db.query(Decision)
        .filter(Decision.title.ilike(f"%{q}%") | Decision.context.ilike(f"%{q}%"))
        .order_by(Decision.created_at.desc())
        .limit(20)
        .all()
    )
    return [
        {
            "decision_id": str(d.id),
            "title": d.title,
            "approver_id": str(d.approver_id) if d.approver_id else None,
            "status": d.status.value,
            "decided_at": d.decided_at,
        }
        for d in rows
    ]


@router.get("/{decision_id}", response_model=DecisionOut)
def get_decision(decision_id: UUID, db: DbSession, _: CurrentUser):
    decision = db.get(Decision, decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    return decision


@router.patch("/{decision_id}", response_model=DecisionOut)
def update_decision(decision_id: UUID, payload: DecisionUpdate, db: DbSession, _: CurrentUser):
    decision = db.get(Decision, decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(decision, key, value)
    if decision.supersedes_id:
        old = db.get(Decision, decision.supersedes_id)
        if old and old.status != DecisionStatus.superseded:
            old.status = DecisionStatus.superseded
    db.commit()
    db.refresh(decision)
    return decision


@router.post("/{decision_id}/links", response_model=DecisionLinkOut, status_code=status.HTTP_201_CREATED)
def add_link(decision_id: UUID, payload: DecisionLinkCreate, db: DbSession, _: CurrentUser):
    decision = db.get(Decision, decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    link = DecisionLink(decision_id=decision_id, **payload.model_dump())
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


@router.get("/{decision_id}/links", response_model=list[DecisionLinkOut])
def list_links(decision_id: UUID, db: DbSession, _: CurrentUser):
    return db.query(DecisionLink).filter(DecisionLink.decision_id == decision_id).all()
