from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.db.models import DecisionStatus, JobStatus, Role


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str | None
    role: Role
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str | None = None
    password: str = Field(min_length=6)
    role: Role = Role.employee


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: Role | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=6)


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None


class ProjectOut(BaseModel):
    id: UUID
    name: str
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentOut(BaseModel):
    id: UUID
    title: str
    filename: str
    content_type: str
    source_system: str
    project_id: UUID | None
    visibility: str
    text_preview: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentUploadResponse(BaseModel):
    document: DocumentOut
    job_id: UUID


class MeetingCreate(BaseModel):
    title: str
    transcript: str
    project_id: UUID | None = None
    occurred_at: datetime | None = None


class MeetingOut(BaseModel):
    id: UUID
    title: str
    project_id: UUID | None
    summary: str | None
    occurred_at: datetime | None
    artifacts: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MeetingIngestResponse(BaseModel):
    meeting: MeetingOut
    job_id: UUID


class JobOut(BaseModel):
    id: UUID
    job_type: str
    status: JobStatus
    document_id: UUID | None
    meeting_id: UUID | None
    error: str | None
    stats: dict | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SearchFilters(BaseModel):
    project_id: UUID | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    types: list[str] | None = None
    source_system: str | None = None
    people: list[str] | None = None


class SearchRequest(BaseModel):
    query: str
    filters: SearchFilters | None = None
    limit: int = Field(default=10, ge=1, le=50)
    mode: str = Field(default="semantic")  # semantic | hybrid


class SearchHit(BaseModel):
    id: str
    score: float
    snippet: str
    source: dict


class SearchResponse(BaseModel):
    results: list[SearchHit]


class ChatSessionOut(BaseModel):
    id: UUID
    title: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatMessageIn(BaseModel):
    content: str


class ChatMessageOut(BaseModel):
    id: UUID
    role: str
    content: str
    confidence: float | None = None
    sources: list | None = None
    related_documents: list | None = None
    related_projects: list | None = None
    people_involved: list | None = None
    timeline: list | None = None
    supporting_evidence: list | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DecisionCreate(BaseModel):
    title: str
    context: str | None = None
    evidence: str | None = None
    alternatives: str | None = None
    expected_outcome: str | None = None
    status: DecisionStatus = DecisionStatus.proposed
    owner_id: UUID | None = None
    approver_id: UUID | None = None
    project_id: UUID | None = None
    decided_at: datetime | None = None
    expiration_date: datetime | None = None
    supersedes_id: UUID | None = None
    links: list[dict] | None = None


class DecisionUpdate(BaseModel):
    title: str | None = None
    context: str | None = None
    evidence: str | None = None
    alternatives: str | None = None
    expected_outcome: str | None = None
    status: DecisionStatus | None = None
    owner_id: UUID | None = None
    approver_id: UUID | None = None
    project_id: UUID | None = None
    decided_at: datetime | None = None
    expiration_date: datetime | None = None
    supersedes_id: UUID | None = None


class DecisionOut(BaseModel):
    id: UUID
    title: str
    context: str | None
    evidence: str | None
    alternatives: str | None
    expected_outcome: str | None
    status: DecisionStatus
    owner_id: UUID | None
    approver_id: UUID | None
    project_id: UUID | None
    decided_at: datetime | None
    expiration_date: datetime | None
    supersedes_id: UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DecisionLinkCreate(BaseModel):
    link_type: str
    target_id: str
    target_title: str | None = None
    source_system: str | None = None


class DecisionLinkOut(BaseModel):
    id: UUID
    decision_id: UUID
    link_type: str
    target_id: str
    target_title: str | None
    source_system: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConnectorConnectRequest(BaseModel):
    credentials: dict
    display_name: str | None = None
    external_account_id: str | None = "default"


class ConnectorAccountOut(BaseModel):
    id: UUID
    provider: str
    external_account_id: str
    display_name: str | None
    status: str
    cursor: str | None
    last_sync_at: datetime | None
    last_error: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConnectorSyncResponse(BaseModel):
    stored: int
    next_cursor: str | None
    stats: dict


class WebhookIngestRequest(BaseModel):
    data: dict


class TimelineEventCreate(BaseModel):
    event_type: str
    title: str
    summary: str | None = None
    project_id: UUID | None = None
    occurred_at: datetime
    source_system: str | None = None
    source_ref: str | None = None
    metadata_json: dict | None = None


class TimelineEventOut(BaseModel):
    id: UUID
    event_type: str
    title: str
    summary: str | None
    project_id: UUID | None
    occurred_at: datetime
    source_system: str | None
    source_ref: str | None
    metadata_json: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ExpertOut(BaseModel):
    person: str
    score: float
    topics: list[str]
    confidence: float
    evidence: list[str]


class ExpertRankResponse(BaseModel):
    experts: list[ExpertOut]


class KnowledgeScoreOut(BaseModel):
    id: UUID
    entity_type: str
    entity_id: str
    freshness: float
    trust: float
    completeness: float
    risk: float
    ownership: str | None
    duplicate_likelihood: float
    suggested_update: str | None
    updated_at: datetime

    model_config = {"from_attributes": True}


class GraphNodeOut(BaseModel):
    id: str
    label: str
    properties: dict


class GraphNeighborResponse(BaseModel):
    node: GraphNodeOut
    neighbors: list[GraphNodeOut]


class GraphSearchRequest(BaseModel):
    label: str | None = None
    name: str | None = None
    limit: int = Field(default=20, ge=1, le=100)


class GraphPathRequest(BaseModel):
    from_id: str
    to_id: str
    max_depth: int = Field(default=3, ge=1, le=3)


class MetricsOverview(BaseModel):
    documents: int
    meetings: int
    decisions: int
    users: int
    jobs_pending: int
    jobs_failed: int
    queries_24h: int
