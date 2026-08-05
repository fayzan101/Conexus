from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import (
    Decision,
    DependencyEdge,
    Document,
    IngestJob,
    JobStatus,
    KnowledgeScore,
    Meeting,
    Opportunity,
    Prediction,
    Project,
    QueryLog,
    Recommendation,
    ResearchReport,
    TimelineEvent,
    WorkflowPattern,
)


def predict_project_delay(db: Session, project: Project) -> Prediction:
    docs = db.query(Document).filter(Document.project_id == project.id).count()
    meetings = db.query(Meeting).filter(Meeting.project_id == project.id).count()
    failed_jobs = (
        db.query(IngestJob)
        .filter(IngestJob.status == JobStatus.failed)
        .count()
    )
    age_proxy = max(1, docs + meetings)
    # Heuristic: low activity + failed jobs => higher delay risk
    probability = min(0.95, 0.2 + (failed_jobs * 0.15) + (0.4 / age_proxy))
    severity = "high" if probability >= 0.7 else "medium" if probability >= 0.4 else "low"
    pred = Prediction(
        prediction_type="project_delay",
        subject_type="project",
        subject_id=str(project.id),
        title=f"Delay risk for {project.name}",
        probability=round(probability, 3),
        severity=severity,
        rationale="Based on project activity density and failed ingest jobs.",
        features={"documents": docs, "meetings": meetings, "failed_jobs": failed_jobs},
    )
    db.add(pred)
    db.commit()
    db.refresh(pred)
    return pred


def predict_knowledge_loss(db: Session) -> list[Prediction]:
    created = []
    risky = (
        db.query(KnowledgeScore)
        .filter(KnowledgeScore.freshness < 0.4)
        .order_by(KnowledgeScore.risk.desc())
        .limit(20)
        .all()
    )
    for score in risky:
        pred = Prediction(
            prediction_type="knowledge_loss",
            subject_type=score.entity_type,
            subject_id=score.entity_id,
            title=f"Knowledge loss risk ({score.entity_type})",
            probability=round(min(0.95, score.risk + (1 - score.freshness) * 0.3), 3),
            severity="high" if score.risk >= 0.6 else "medium",
            rationale=score.suggested_update or "Stale or incomplete knowledge detected.",
            features={
                "freshness": score.freshness,
                "trust": score.trust,
                "risk": score.risk,
            },
        )
        db.add(pred)
        created.append(pred)
    db.commit()
    return created


def run_predictions(db: Session) -> dict:
    projects = db.query(Project).limit(50).all()
    project_preds = [predict_project_delay(db, p) for p in projects]
    loss_preds = predict_knowledge_loss(db)
    return {
        "project_delay": len(project_preds),
        "knowledge_loss": len(loss_preds),
    }


def detect_workflow_patterns(db: Session) -> list[WorkflowPattern]:
    """Detect repetitive query/ingest patterns as automation candidates."""
    since = datetime.now(timezone.utc) - timedelta(days=30)
    queries = (
        db.query(QueryLog.query_text, func.count(QueryLog.id))
        .filter(QueryLog.created_at >= since)
        .group_by(QueryLog.query_text)
        .having(func.count(QueryLog.id) >= 2)
        .all()
    )
    patterns: list[WorkflowPattern] = []
    for text, count in queries:
        key = f"query:{text.strip().lower()[:80]}"
        existing = db.query(WorkflowPattern).filter(WorkflowPattern.pattern_key == key).first()
        suggestion = "Create a saved answer or automation for this recurring question."
        if existing:
            existing.occurrences = int(count)
            existing.suggestion = suggestion
            existing.automation_type = "notification"
            existing.sample_evidence = [text]
            patterns.append(existing)
        else:
            row = WorkflowPattern(
                name=f"Recurring query: {text[:60]}",
                pattern_key=key,
                occurrences=int(count),
                suggestion=suggestion,
                automation_type="ai_agent",
                sample_evidence=[text],
            )
            db.add(row)
            patterns.append(row)

    # Ingest failure loops
    failed = db.query(IngestJob).filter(IngestJob.status == JobStatus.failed).count()
    if failed >= 2:
        key = "ingest:failures"
        existing = db.query(WorkflowPattern).filter(WorkflowPattern.pattern_key == key).first()
        if existing:
            existing.occurrences = failed
            patterns.append(existing)
        else:
            row = WorkflowPattern(
                name="Repeated ingest failures",
                pattern_key=key,
                occurrences=failed,
                suggestion="Add retry policy / alerting for ingest pipeline failures.",
                automation_type="rpa",
                sample_evidence=["ingest_jobs.failed"],
            )
            db.add(row)
            patterns.append(row)

    db.commit()
    return patterns


def upsert_dependency(
    db: Session,
    *,
    from_type: str,
    from_id: str,
    to_type: str,
    to_id: str,
    rel_type: str = "depends_on",
    criticality: float = 0.5,
    metadata_json: dict | None = None,
) -> DependencyEdge:
    existing = (
        db.query(DependencyEdge)
        .filter(
            DependencyEdge.from_id == from_id,
            DependencyEdge.to_id == to_id,
            DependencyEdge.rel_type == rel_type,
        )
        .first()
    )
    if existing:
        existing.criticality = criticality
        existing.metadata_json = metadata_json
        db.commit()
        db.refresh(existing)
        return existing
    edge = DependencyEdge(
        from_type=from_type,
        from_id=from_id,
        to_type=to_type,
        to_id=to_id,
        rel_type=rel_type,
        criticality=criticality,
        metadata_json=metadata_json,
    )
    db.add(edge)
    db.commit()
    db.refresh(edge)
    return edge


def impact_analysis(db: Session, node_id: str, *, depth: int = 2) -> dict:
    visited = {node_id}
    frontier = [node_id]
    edges_out = []
    for _ in range(max(1, depth)):
        nxt = []
        for nid in frontier:
            rows = db.query(DependencyEdge).filter(DependencyEdge.from_id == nid).all()
            for e in rows:
                edges_out.append(
                    {
                        "from_id": e.from_id,
                        "from_type": e.from_type,
                        "to_id": e.to_id,
                        "to_type": e.to_type,
                        "rel_type": e.rel_type,
                        "criticality": e.criticality,
                    }
                )
                if e.to_id not in visited:
                    visited.add(e.to_id)
                    nxt.append(e.to_id)
        frontier = nxt
        if not frontier:
            break
    return {"root": node_id, "impacted_nodes": sorted(visited - {node_id}), "edges": edges_out}


def discover_opportunities(db: Session) -> list[Opportunity]:
    created: list[Opportunity] = []
    # Documentation gaps from knowledge scores
    gaps = (
        db.query(KnowledgeScore)
        .filter(KnowledgeScore.completeness < 0.35)
        .order_by(KnowledgeScore.completeness.asc())
        .limit(10)
        .all()
    )
    for g in gaps:
        opp = Opportunity(
            category="documentation_gap",
            title=f"Improve {g.entity_type} completeness",
            description=g.suggested_update or "Content appears incomplete.",
            score=round(1.0 - g.completeness, 3),
            evidence=[{"entity_id": g.entity_id, "completeness": g.completeness}],
        )
        db.add(opp)
        created.append(opp)

    # Repeated complaints / queries as product opportunity signal
    since = datetime.now(timezone.utc) - timedelta(days=30)
    top_queries = (
        db.query(QueryLog.query_text, func.count(QueryLog.id))
        .filter(QueryLog.created_at >= since)
        .group_by(QueryLog.query_text)
        .having(func.count(QueryLog.id) >= 3)
        .limit(5)
        .all()
    )
    for text, count in top_queries:
        opp = Opportunity(
            category="repeated_demand",
            title=f"Address recurring question",
            description=text[:300],
            score=min(0.95, 0.4 + count * 0.1),
            evidence=[{"query": text, "count": int(count)}],
        )
        db.add(opp)
        created.append(opp)

    db.commit()
    return created


def generate_recommendations(db: Session) -> list[Recommendation]:
    recs: list[Recommendation] = []
    high_preds = (
        db.query(Prediction)
        .filter(Prediction.probability >= 0.6)
        .order_by(Prediction.probability.desc())
        .limit(10)
        .all()
    )
    for p in high_preds:
        rec = Recommendation(
            category="risk_mitigation",
            title=f"Mitigate: {p.title}",
            action=p.rationale or "Investigate and reduce predicted risk.",
            priority="high" if p.severity == "high" else "medium",
            confidence=p.probability,
            related_refs=[{"prediction_id": str(p.id), "subject_id": p.subject_id}],
        )
        db.add(rec)
        recs.append(rec)

    patterns = db.query(WorkflowPattern).filter(WorkflowPattern.occurrences >= 2).limit(10).all()
    for wp in patterns:
        rec = Recommendation(
            category="automation",
            title=f"Automate: {wp.name}",
            action=wp.suggestion or "Automate this recurring workflow.",
            priority="medium",
            confidence=min(0.9, 0.4 + wp.occurrences * 0.05),
            related_refs=[{"pattern_key": wp.pattern_key}],
        )
        db.add(rec)
        recs.append(rec)

    db.commit()
    return recs


def run_research_agent(db: Session, *, problem: str, user_id=None) -> ResearchReport:
    """Deterministic multi-step research workflow for MVP Phase 3."""
    # 1) Collect evidence from docs/meetings/timeline/decisions
    like = f"%{problem.split()[0] if problem.split() else problem}%"
    docs = db.query(Document).filter(Document.title.ilike(like) | Document.text_preview.ilike(like)).limit(5).all()
    meetings = db.query(Meeting).filter(Meeting.title.ilike(like) | Meeting.transcript.ilike(like)).limit(5).all()
    decisions = db.query(Decision).filter(Decision.title.ilike(like) | Decision.context.ilike(like)).limit(5).all()
    events = db.query(TimelineEvent).filter(TimelineEvent.title.ilike(like)).limit(5).all()

    evidence = []
    for d in docs:
        evidence.append({"type": "document", "id": str(d.id), "title": d.title, "snippet": (d.text_preview or "")[:240]})
    for m in meetings:
        evidence.append({"type": "meeting", "id": str(m.id), "title": m.title, "snippet": (m.summary or m.transcript or "")[:240]})
    for d in decisions:
        evidence.append({"type": "decision", "id": str(d.id), "title": d.title, "snippet": (d.context or "")[:240]})
    for e in events:
        evidence.append({"type": "timeline", "id": str(e.id), "title": e.title, "snippet": (e.summary or "")[:240]})

    # 2) Detect patterns
    type_counts = Counter(item["type"] for item in evidence)
    patterns = [{"signal": k, "count": v} for k, v in type_counts.most_common()]

    # 3) Root cause heuristic
    if not evidence:
        root = "Insufficient evidence in the knowledge base to determine a root cause."
        recs = ["Ingest related documents, meetings, and decisions, then re-run research."]
        summary = f"Research on '{problem}' found no accessible evidence."
    else:
        dominant = patterns[0]["signal"] if patterns else "unknown"
        root = f"Primary signals concentrate in '{dominant}' sources related to the problem statement."
        recs = [
            f"Review the top {dominant} evidence items and validate assumptions.",
            "Create or update a Decision record capturing the chosen remediation.",
            "Add monitoring/automation if the issue is recurring.",
        ]
        summary = (
            f"Executive summary: Investigated '{problem}'. Collected {len(evidence)} evidence items. "
            f"Dominant source type: {dominant}. Recommended next actions: {recs[0]}"
        )

    report = ResearchReport(
        problem=problem,
        status="completed",
        evidence=evidence,
        patterns=patterns,
        root_cause=root,
        recommendations=recs,
        executive_summary=summary,
        created_by=user_id,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def executive_kpis(db: Session) -> dict:
    docs = db.query(func.count(Document.id)).scalar() or 0
    decisions = db.query(func.count(Decision.id)).scalar() or 0
    preds = db.query(func.count(Prediction.id)).scalar() or 0
    high_risk = (
        db.query(func.count(Prediction.id)).filter(Prediction.severity == "high").scalar() or 0
    )
    workflows = db.query(func.count(WorkflowPattern.id)).scalar() or 0
    opps = db.query(func.count(Opportunity.id)).filter(Opportunity.status == "open").scalar() or 0
    recs = (
        db.query(func.count(Recommendation.id)).filter(Recommendation.status == "proposed").scalar()
        or 0
    )
    avg_fresh = db.query(func.avg(KnowledgeScore.freshness)).scalar()
    knowledge_health = round(float(avg_fresh or 0.5), 3)
    return {
        "knowledge_health": knowledge_health,
        "decision_count": decisions,
        "document_count": docs,
        "prediction_count": preds,
        "high_risk_predictions": high_risk,
        "workflow_automation_candidates": workflows,
        "open_opportunities": opps,
        "open_recommendations": recs,
        "decision_velocity_proxy": decisions,  # simplified KPI for Phase 3
    }
