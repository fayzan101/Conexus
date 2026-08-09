from __future__ import annotations

import re
import uuid
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import EntityMergeAudit, EntityRecord


def _canonical_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")


def upsert_entity(
    db: Session,
    *,
    tenant_id: str,
    entity_type: str,
    display_name: str,
    aliases: list[str] | None = None,
) -> EntityRecord:
    key = _canonical_key(display_name)
    row = (
        db.query(EntityRecord)
        .filter(
            EntityRecord.tenant_id == tenant_id,
            EntityRecord.entity_type == entity_type,
            EntityRecord.canonical_key == key,
            EntityRecord.merged_into_id.is_(None),
        )
        .first()
    )
    if row:
        merged_aliases = list(dict.fromkeys((row.aliases or []) + (aliases or [])))
        row.aliases = merged_aliases
        db.commit()
        db.refresh(row)
        return row
    row = EntityRecord(
        tenant_id=tenant_id,
        entity_type=entity_type,
        canonical_key=key,
        display_name=display_name,
        aliases=aliases or [],
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def find_duplicates(db: Session, *, tenant_id: str, entity_type: str) -> list[dict]:
    rows = (
        db.query(EntityRecord)
        .filter(
            EntityRecord.tenant_id == tenant_id,
            EntityRecord.entity_type == entity_type,
            EntityRecord.merged_into_id.is_(None),
        )
        .all()
    )
    by_norm: dict[str, list[EntityRecord]] = {}
    for row in rows:
        norms = {_canonical_key(row.display_name)}
        for alias in row.aliases or []:
            norms.add(_canonical_key(alias))
        for n in norms:
            by_norm.setdefault(n, []).append(row)

    seen: set[uuid.UUID] = set()
    groups = []
    for items in by_norm.values():
        uniq = []
        for item in items:
            if item.id not in seen:
                uniq.append(item)
                seen.add(item.id)
        if len(uniq) > 1:
            groups.append(
                {
                    "entity_type": entity_type,
                    "candidates": [
                        {"id": str(i.id), "display_name": i.display_name, "aliases": i.aliases or []}
                        for i in uniq
                    ],
                }
            )
    return groups


def merge_entities(
    db: Session,
    *,
    tenant_id: str,
    source_id: UUID,
    target_id: UUID,
    reason: str | None,
    user_id: UUID | None,
) -> EntityRecord:
    source = db.get(EntityRecord, source_id)
    target = db.get(EntityRecord, target_id)
    if not source or not target:
        raise ValueError("Entity not found")
    if source.tenant_id != tenant_id or target.tenant_id != tenant_id:
        raise ValueError("Cross-tenant merge forbidden")
    if source.id == target.id:
        raise ValueError("Cannot merge entity into itself")

    aliases = list(dict.fromkeys((target.aliases or []) + [source.display_name] + (source.aliases or [])))
    target.aliases = aliases
    source.merged_into_id = target.id
    db.add(
        EntityMergeAudit(
            tenant_id=tenant_id,
            source_entity_id=source.id,
            target_entity_id=target.id,
            reason=reason or "duplicate",
            created_by=user_id,
        )
    )
    db.commit()
    db.refresh(target)
    return target
