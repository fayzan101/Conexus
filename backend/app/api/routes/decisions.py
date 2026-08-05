from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.db.models import Decision
from app.deps import CurrentUser, DbSession
from app.schemas import DecisionCreate, DecisionOut, DecisionUpdate

router = APIRouter(prefix="/v1/decisions", tags=["decisions"])


@router.get("", response_model=list[DecisionOut])
def list_decisions(db: DbSession, _: CurrentUser):
    return db.query(Decision).order_by(Decision.created_at.desc()).limit(100).all()


@router.post("", response_model=DecisionOut, status_code=status.HTTP_201_CREATED)
def create_decision(payload: DecisionCreate, db: DbSession, _: CurrentUser):
    decision = Decision(**payload.model_dump())
    db.add(decision)
    db.commit()
    db.refresh(decision)
    return decision


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
    db.commit()
    db.refresh(decision)
    return decision
