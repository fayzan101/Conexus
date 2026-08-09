from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.db.models import PendingMemoryLink, Role, User
from app.deps import AppSettings, CurrentUser, DbSession, require_roles
from app.services.entity_resolution import find_duplicates, merge_entities, upsert_entity
from app.services.events import event_bus_metrics, get_event_bus
from app.services.memory_links import confirm_link

router = APIRouter(prefix="/v1/knowledge", tags=["knowledge"])


class EntityUpsertRequest(BaseModel):
    entity_type: str = Field(pattern="^(person|project)$")
    display_name: str
    aliases: list[str] | None = None


class EntityMergeRequest(BaseModel):
    source_id: UUID
    target_id: UUID
    reason: str | None = None


class LinkReviewRequest(BaseModel):
    accept: bool = True


@router.post("/entities")
def create_entity(payload: EntityUpsertRequest, db: DbSession, user: CurrentUser):
    row = upsert_entity(
        db,
        tenant_id=user.tenant_id,
        entity_type=payload.entity_type,
        display_name=payload.display_name,
        aliases=payload.aliases,
    )
    return {
        "id": str(row.id),
        "entity_type": row.entity_type,
        "display_name": row.display_name,
        "aliases": row.aliases or [],
        "canonical_key": row.canonical_key,
    }


@router.get("/entities/duplicates")
def duplicates(db: DbSession, user: CurrentUser, entity_type: str = "person"):
    return {"groups": find_duplicates(db, tenant_id=user.tenant_id, entity_type=entity_type)}


@router.post("/entities/merge")
def merge(
    payload: EntityMergeRequest,
    db: DbSession,
    user: Annotated[User, Depends(require_roles(Role.admin, Role.knowledge_manager))],
):
    try:
        target = merge_entities(
            db,
            tenant_id=user.tenant_id,
            source_id=payload.source_id,
            target_id=payload.target_id,
            reason=payload.reason,
            user_id=user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"id": str(target.id), "aliases": target.aliases or []}


@router.get("/links/pending")
def pending_links(db: DbSession, user: CurrentUser):
    rows = (
        db.query(PendingMemoryLink)
        .filter(PendingMemoryLink.tenant_id == user.tenant_id, PendingMemoryLink.status == "proposed")
        .order_by(PendingMemoryLink.created_at.desc())
        .limit(100)
        .all()
    )
    return [
        {
            "id": str(r.id),
            "link_type": r.link_type,
            "target_id": r.target_id,
            "source_ref": r.source_ref,
            "title": r.title,
            "confidence": r.confidence,
            "rationale": r.rationale,
            "status": r.status,
        }
        for r in rows
    ]


@router.post("/links/{link_id}/review")
def review_link(
    link_id: UUID,
    payload: LinkReviewRequest,
    db: DbSession,
    user: Annotated[User, Depends(require_roles(Role.admin, Role.knowledge_manager, Role.manager))],
):
    try:
        row = confirm_link(db, tenant_id=user.tenant_id, link_id=link_id, user_id=user.id, accept=payload.accept)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"id": str(row.id), "status": row.status}


@router.get("/events/metrics")
def bus_metrics(settings: AppSettings, _: CurrentUser):
    bus = get_event_bus(settings)
    return {**event_bus_metrics(), "depth": bus.depth(), "backend": settings.event_bus_backend}
