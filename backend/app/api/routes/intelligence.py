from fastapi import APIRouter

from app.deps import CurrentUser, DbSession
from app.schemas import ExpertRankResponse, KnowledgeScoreOut
from app.db.models import KnowledgeScore
from app.services.intelligence import (
    harvest_expertise_from_meetings,
    rank_experts,
    refresh_document_scores,
)

router = APIRouter(tags=["intelligence"])


@router.get("/v1/expertise", response_model=ExpertRankResponse)
def expertise(db: DbSession, _: CurrentUser, topic: str | None = None, limit: int = 10):
    return ExpertRankResponse(experts=rank_experts(db, topic=topic, limit=limit))


@router.post("/v1/expertise/harvest")
def harvest(db: DbSession, _: CurrentUser):
    count = harvest_expertise_from_meetings(db)
    return {"signals_created": count}


@router.get("/v1/freshness", response_model=list[KnowledgeScoreOut])
def freshness(db: DbSession, _: CurrentUser, limit: int = 50):
    return (
        db.query(KnowledgeScore)
        .order_by(KnowledgeScore.risk.desc())
        .limit(limit)
        .all()
    )


@router.post("/v1/freshness/refresh")
def freshness_refresh(db: DbSession, _: CurrentUser):
    count = refresh_document_scores(db)
    return {"scored": count}
