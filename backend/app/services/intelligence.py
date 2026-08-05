from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.models import Document, ExpertiseSignal, KnowledgeScore, Meeting


def score_document_freshness(doc: Document, *, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    created = doc.created_at or now
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    age_days = max(0.0, (now - created).total_seconds() / 86400.0)
    freshness = max(0.05, min(1.0, 1.0 - (age_days / 365.0)))
    preview = doc.text_preview or ""
    completeness = min(1.0, len(preview) / 2000.0) if preview else 0.1
    trust = 0.7 if doc.source_system == "upload" else 0.8
    duplicate_likelihood = 0.1
    risk = round(1.0 - ((freshness + trust + completeness) / 3.0), 3)
    suggested = None
    if freshness < 0.4:
        suggested = "Review and refresh this document; content may be stale."
    elif completeness < 0.3:
        suggested = "Expand documentation; content appears incomplete."
    return {
        "freshness": round(freshness, 3),
        "trust": trust,
        "completeness": round(completeness, 3),
        "risk": risk,
        "ownership": None,
        "duplicate_likelihood": duplicate_likelihood,
        "suggested_update": suggested,
    }


def upsert_knowledge_score(db: Session, *, entity_type: str, entity_id: str, scores: dict) -> KnowledgeScore:
    row = (
        db.query(KnowledgeScore)
        .filter(KnowledgeScore.entity_type == entity_type, KnowledgeScore.entity_id == entity_id)
        .first()
    )
    if not row:
        row = KnowledgeScore(entity_type=entity_type, entity_id=entity_id)
        db.add(row)
    for key, value in scores.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def refresh_document_scores(db: Session) -> int:
    count = 0
    for doc in db.query(Document).limit(500).all():
        scores = score_document_freshness(doc)
        upsert_knowledge_score(db, entity_type="document", entity_id=str(doc.id), scores=scores)
        count += 1
    return count


def record_expertise_from_text(
    db: Session,
    *,
    person_key: str,
    text: str,
    source_system: str,
    weight: float = 1.0,
) -> list[ExpertiseSignal]:
    from app.services.ingest import extract_entities

    entities = extract_entities(text)
    topics = entities["projects"] or ["general"]
    created = []
    for topic in topics[:5]:
        signal = ExpertiseSignal(
            person_key=person_key,
            topic=topic,
            weight=weight,
            evidence=text[:300],
            source_system=source_system,
        )
        db.add(signal)
        created.append(signal)
    db.commit()
    return created


def rank_experts(db: Session, *, topic: str | None = None, limit: int = 10) -> list[dict]:
    q = db.query(ExpertiseSignal)
    if topic:
        q = q.filter(ExpertiseSignal.topic.ilike(f"%{topic}%"))
    rows = q.all()
    scores: dict[str, float] = defaultdict(float)
    evidence: dict[str, list[str]] = defaultdict(list)
    topics_map: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        scores[row.person_key] += float(row.weight)
        topics_map[row.person_key].add(row.topic)
        if row.evidence:
            evidence[row.person_key].append(row.evidence)
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:limit]
    out = []
    for person, score in ranked:
        out.append(
            {
                "person": person,
                "score": round(score, 3),
                "topics": sorted(topics_map[person]),
                "confidence": round(min(0.99, score / (score + 3.0)), 3),
                "evidence": evidence[person][:3],
            }
        )
    return out


def harvest_expertise_from_meetings(db: Session) -> int:
    count = 0
    for meeting in db.query(Meeting).limit(200).all():
        entities = __import__("app.services.ingest", fromlist=["extract_entities"]).extract_entities(
            meeting.transcript or ""
        )
        for person in entities["people"]:
            record_expertise_from_text(
                db,
                person_key=person,
                text=meeting.summary or meeting.transcript[:500],
                source_system="meeting",
                weight=1.5,
            )
            count += 1
    return count
