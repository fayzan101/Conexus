from datetime import datetime, timezone

from app.db.models import Document, KnowledgeScore, Project, QueryLog
from app.services.operating_system import (
    detect_workflow_patterns,
    discover_opportunities,
    executive_kpis,
    generate_recommendations,
    impact_analysis,
    predict_project_delay,
    run_research_agent,
    upsert_dependency,
)


def test_predict_project_delay(db, seeded_db):
    project = Project(name="Phoenix-OS", description="phase3")
    seeded_db.add(project)
    seeded_db.commit()
    pred = predict_project_delay(seeded_db, project)
    assert pred.prediction_type == "project_delay"
    assert 0 <= pred.probability <= 1


def test_workflow_and_opportunities(db, seeded_db, test_settings):
    from app.db.models import User

    user = seeded_db.query(User).filter_by(email=test_settings.dev_user_email).one()
    for _ in range(3):
        seeded_db.add(QueryLog(user_id=user.id, query_type="search", query_text="Why Kubernetes?"))
    seeded_db.commit()

    patterns = detect_workflow_patterns(seeded_db)
    assert any(p.pattern_key.startswith("query:") for p in patterns)

    doc = Document(
        title="Thin doc",
        filename="t.txt",
        content_type="text/plain",
        object_key="x",
        text_preview="short",
        source_system="upload",
    )
    seeded_db.add(doc)
    seeded_db.commit()
    seeded_db.add(
        KnowledgeScore(
            entity_type="document",
            entity_id=str(doc.id),
            freshness=0.2,
            trust=0.5,
            completeness=0.1,
            risk=0.8,
            duplicate_likelihood=0.1,
            suggested_update="Expand doc",
        )
    )
    seeded_db.commit()
    opps = discover_opportunities(seeded_db)
    assert opps


def test_dependency_impact(db, seeded_db):
    upsert_dependency(
        seeded_db,
        from_type="service",
        from_id="api",
        to_type="database",
        to_id="postgres",
        criticality=0.9,
    )
    upsert_dependency(
        seeded_db,
        from_type="web",
        from_id="frontend",
        to_type="service",
        to_id="api",
        criticality=0.7,
    )
    impact = impact_analysis(seeded_db, "frontend", depth=2)
    assert "api" in impact["impacted_nodes"]
    assert "postgres" in impact["impacted_nodes"]


def test_research_agent_and_exec_kpis(db, seeded_db):
    seeded_db.add(
        Document(
            title="Outage report",
            filename="o.txt",
            content_type="text/plain",
            object_key="o",
            text_preview="Root cause was dependency on Service Y.",
            source_system="upload",
        )
    )
    seeded_db.commit()
    report = run_research_agent(seeded_db, problem="Service Y outage")
    assert report.executive_summary
    assert report.root_cause

    generate_recommendations(seeded_db)
    kpis = executive_kpis(seeded_db)
    assert "knowledge_health" in kpis
    assert kpis["document_count"] >= 1
