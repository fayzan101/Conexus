from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.db.models import (
    DependencyEdge,
    Opportunity,
    Prediction,
    Recommendation,
    ResearchReport,
    WorkflowPattern,
)
from app.deps import CurrentUser, DbSession
from app.schemas import (
    DependencyCreate,
    DependencyOut,
    ExecutiveDashboardOut,
    OpportunityOut,
    PredictionOut,
    RecommendationOut,
    ResearchReportOut,
    ResearchRequest,
    WorkflowPatternOut,
)
from app.services.operating_system import (
    detect_workflow_patterns,
    discover_opportunities,
    executive_kpis,
    generate_recommendations,
    impact_analysis,
    run_predictions,
    run_research_agent,
    upsert_dependency,
)

router = APIRouter(tags=["operating-system"])


@router.post("/v1/predictions/run")
def predictions_run(db: DbSession, _: CurrentUser):
    return run_predictions(db)


@router.get("/v1/predictions", response_model=list[PredictionOut])
def predictions_list(db: DbSession, _: CurrentUser, limit: int = 50):
    return db.query(Prediction).order_by(Prediction.created_at.desc()).limit(limit).all()


@router.post("/v1/workflows/detect", response_model=list[WorkflowPatternOut])
def workflows_detect(db: DbSession, _: CurrentUser):
    return detect_workflow_patterns(db)


@router.get("/v1/workflows", response_model=list[WorkflowPatternOut])
def workflows_list(db: DbSession, _: CurrentUser):
    return db.query(WorkflowPattern).order_by(WorkflowPattern.occurrences.desc()).limit(100).all()


@router.post("/v1/dependencies", response_model=DependencyOut, status_code=201)
def dependencies_create(payload: DependencyCreate, db: DbSession, _: CurrentUser):
    return upsert_dependency(db, **payload.model_dump())


@router.get("/v1/dependencies", response_model=list[DependencyOut])
def dependencies_list(db: DbSession, _: CurrentUser, limit: int = 100):
    return db.query(DependencyEdge).order_by(DependencyEdge.created_at.desc()).limit(limit).all()


@router.get("/v1/dependencies/impact/{node_id}")
def dependencies_impact(node_id: str, db: DbSession, _: CurrentUser, depth: int = 2):
    return impact_analysis(db, node_id, depth=depth)


@router.post("/v1/opportunities/discover", response_model=list[OpportunityOut])
def opportunities_discover(db: DbSession, _: CurrentUser):
    return discover_opportunities(db)


@router.get("/v1/opportunities", response_model=list[OpportunityOut])
def opportunities_list(db: DbSession, _: CurrentUser):
    return db.query(Opportunity).order_by(Opportunity.score.desc()).limit(100).all()


@router.post("/v1/recommendations/generate", response_model=list[RecommendationOut])
def recommendations_generate(db: DbSession, _: CurrentUser):
    return generate_recommendations(db)


@router.get("/v1/recommendations", response_model=list[RecommendationOut])
def recommendations_list(db: DbSession, _: CurrentUser):
    return db.query(Recommendation).order_by(Recommendation.created_at.desc()).limit(100).all()


@router.post("/v1/research/run", response_model=ResearchReportOut)
def research_run(payload: ResearchRequest, db: DbSession, user: CurrentUser):
    return run_research_agent(db, problem=payload.problem, user_id=user.id)


@router.get("/v1/research", response_model=list[ResearchReportOut])
def research_list(db: DbSession, _: CurrentUser):
    return db.query(ResearchReport).order_by(ResearchReport.created_at.desc()).limit(50).all()


@router.get("/v1/research/{report_id}", response_model=ResearchReportOut)
def research_get(report_id: UUID, db: DbSession, _: CurrentUser):
    report = db.get(ResearchReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.get("/v1/executive/dashboard", response_model=ExecutiveDashboardOut)
def executive_dashboard(db: DbSession, _: CurrentUser):
    return ExecutiveDashboardOut(**executive_kpis(db))
