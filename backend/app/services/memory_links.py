from __future__ import annotations

import re
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import Decision, DecisionLink, Document, PendingMemoryLink, Project


def _score_overlap(text: str, needle: str) -> float:
    if not text or not needle:
        return 0.0
    t = text.lower()
    n = needle.lower()
    if n in t:
        return 0.9
    tokens = [tok for tok in re.split(r"\W+", n) if len(tok) > 2]
    if not tokens:
        return 0.0
    hits = sum(1 for tok in tokens if tok in t)
    return hits / len(tokens)


def propose_links_for_document(
    db: Session,
    settings: Settings,
    *,
    tenant_id: str,
    document: Document,
) -> list[PendingMemoryLink]:
    text = f"{document.title}\n{document.text_preview or ''}"
    created: list[PendingMemoryLink] = []

    projects = db.query(Project).filter(Project.tenant_id == tenant_id).all()
    for project in projects:
        conf = _score_overlap(text, project.name)
        if conf < settings.auto_link_min_confidence:
            continue
        pending = PendingMemoryLink(
            tenant_id=tenant_id,
            link_type="project",
            target_id=str(project.id),
            source_ref=str(document.id),
            source_system=document.source_system,
            title=document.title,
            confidence=round(conf, 3),
            status="proposed",
            rationale=f"Document mentions project '{project.name}'",
        )
        db.add(pending)
        created.append(pending)

    decisions = db.query(Decision).filter(Decision.tenant_id == tenant_id).all()
    for decision in decisions:
        conf = max(_score_overlap(text, decision.title), _score_overlap(text, decision.context or ""))
        if conf < settings.auto_link_min_confidence:
            continue
        # Prefer issue/pr/message artifact types from connectors
        link_type = "document"
        if document.source_system in {"github", "jira"}:
            link_type = "issue"
        pending = PendingMemoryLink(
            tenant_id=tenant_id,
            link_type="decision",
            target_id=str(decision.id),
            source_ref=str(document.id),
            source_system=document.source_system,
            title=document.title,
            confidence=round(conf, 3),
            status="proposed",
            rationale=f"Likely evidence for decision '{decision.title}'",
        )
        db.add(pending)
        created.append(pending)

    db.commit()
    for row in created:
        db.refresh(row)
    return created


def confirm_link(db: Session, *, tenant_id: str, link_id: UUID, user_id: UUID, accept: bool) -> PendingMemoryLink:
    link = db.get(PendingMemoryLink, link_id)
    if not link or link.tenant_id != tenant_id:
        raise ValueError("Pending link not found")
    link.status = "confirmed" if accept else "rejected"
    link.reviewed_at = datetime.now(timezone.utc)
    link.reviewed_by = user_id
    if accept and link.link_type == "decision":
        db.add(
            DecisionLink(
                decision_id=UUID(link.target_id),
                link_type="document",
                target_id=link.source_ref,
                target_title=link.title,
                source_system=link.source_system,
            )
        )
    if accept and link.link_type == "project":
        doc = db.get(Document, UUID(link.source_ref))
        if doc and doc.tenant_id == tenant_id:
            doc.project_id = UUID(link.target_id)
    db.commit()
    db.refresh(link)
    return link
