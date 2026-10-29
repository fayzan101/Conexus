import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _str_enum(enum_cls: type[enum.Enum]):
    return Enum(
        enum_cls,
        name=enum_cls.__name__.lower(),
        native_enum=False,
        values_callable=lambda obj: [e.value for e in obj],
    )


class Role(str, enum.Enum):
    employee = "employee"
    admin = "admin"
    manager = "manager"
    auditor = "auditor"
    knowledge_manager = "knowledge_manager"
    ai_administrator = "ai_administrator"


class JobStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    dead_lettered = "dead_lettered"


class DecisionStatus(str, enum.Enum):
    proposed = "proposed"
    approved = "approved"
    rejected = "rejected"
    superseded = "superseded"
    expired = "expired"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    email: Mapped[str] = mapped_column(String(320), index=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    idp_subject: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    scim_external_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    region: Mapped[str | None] = mapped_column(String(64), nullable=True)
    clearance: Mapped[str] = mapped_column(String(32), default="internal")  # public|internal|confidential|restricted
    role: Mapped[Role] = mapped_column(_str_enum(Role), default=Role.employee)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    documents: Mapped[list["Document"]] = relationship(back_populates="uploaded_by_user")


class InviteToken(Base):
    __tablename__ = "invite_tokens"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    email: Mapped[str] = mapped_column(String(320), index=True)
    role: Mapped[Role] = mapped_column(_str_enum(Role), default=Role.employee)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    invited_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_projects_tenant_name"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    title: Mapped[str] = mapped_column(String(512))
    filename: Mapped[str] = mapped_column(String(512))
    content_type: Mapped[str] = mapped_column(String(128), default="application/octet-stream")
    object_key: Mapped[str] = mapped_column(String(1024))
    source_system: Mapped[str] = mapped_column(String(64), default="upload")
    project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    visibility: Mapped[str] = mapped_column(String(32), default="org")
    classification: Mapped[str] = mapped_column(String(32), default="internal")
    region: Mapped[str | None] = mapped_column(String(64), nullable=True)
    legal_hold: Mapped[bool] = mapped_column(Boolean, default=False)
    retain_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    text_preview: Mapped[str | None] = mapped_column(Text, nullable=True)
    search_vector: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    uploaded_by_user: Mapped[User | None] = relationship(back_populates="documents")
    chunks: Mapped[list["DocumentChunk"]] = relationship(back_populates="document")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (UniqueConstraint("document_id", "chunk_index"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    vector_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    document: Mapped[Document] = relationship(back_populates="chunks")


class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    title: Mapped[str] = mapped_column(String(512))
    project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    transcript: Mapped[str] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    artifacts: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IngestJob(Base):
    __tablename__ = "ingest_jobs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    job_type: Mapped[str] = mapped_column(String(64))
    status: Mapped[JobStatus] = mapped_column(_str_enum(JobStatus), default=JobStatus.pending)
    document_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("documents.id"), nullable=True)
    meeting_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("meetings.id"), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    stats: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    dead_lettered: Mapped[bool] = mapped_column(Boolean, default=False)
    queued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Decision(Base):
    __tablename__ = "decisions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    title: Mapped[str] = mapped_column(String(512))
    context: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    alternatives: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[DecisionStatus] = mapped_column(
        _str_enum(DecisionStatus), default=DecisionStatus.proposed
    )
    owner_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approver_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expiration_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    supersedes_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("decisions.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    messages: Mapped[list["ChatMessage"]] = relationship(back_populates="session")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chat_sessions.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(32))
    content: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    sources: Mapped[list | None] = mapped_column(JSON, nullable=True)
    related: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped[ChatSession] = relationship(back_populates="messages")


class QueryLog(Base):
    __tablename__ = "query_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    query_type: Mapped[str] = mapped_column(String(32))
    query_text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ConnectorAccount(Base):
    __tablename__ = "connector_accounts"
    __table_args__ = (UniqueConstraint("tenant_id", "provider", "external_account_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    provider: Mapped[str] = mapped_column(String(64), index=True)
    external_account_id: Mapped[str] = mapped_column(String(255), default="default")
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="connected")
    credentials: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    cursor: Mapped[str | None] = mapped_column(String(512), nullable=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    health_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    health_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DecisionLink(Base):
    __tablename__ = "decision_links"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    decision_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("decisions.id", ondelete="CASCADE"))
    link_type: Mapped[str] = mapped_column(String(64))  # document|meeting|issue|pr|message
    target_id: Mapped[str] = mapped_column(String(255))
    target_title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source_system: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TimelineEvent(Base):
    __tablename__ = "timeline_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(512))
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    source_system: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ExpertiseSignal(Base):
    __tablename__ = "expertise_signals"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    person_key: Mapped[str] = mapped_column(String(255), index=True)
    topic: Mapped[str] = mapped_column(String(255), index=True)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_system: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class KnowledgeScore(Base):
    __tablename__ = "knowledge_scores"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    entity_type: Mapped[str] = mapped_column(String(64), index=True)
    entity_id: Mapped[str] = mapped_column(String(255), index=True)
    freshness: Mapped[float] = mapped_column(Float, default=0.5)
    trust: Mapped[float] = mapped_column(Float, default=0.5)
    completeness: Mapped[float] = mapped_column(Float, default=0.5)
    risk: Mapped[float] = mapped_column(Float, default=0.5)
    ownership: Mapped[str | None] = mapped_column(String(255), nullable=True)
    duplicate_likelihood: Mapped[float] = mapped_column(Float, default=0.0)
    suggested_update: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    prediction_type: Mapped[str] = mapped_column(String(64), index=True)
    subject_type: Mapped[str] = mapped_column(String(64))
    subject_id: Mapped[str] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(512))
    probability: Mapped[float] = mapped_column(Float, default=0.5)
    severity: Mapped[str] = mapped_column(String(32), default="medium")
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    features: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WorkflowPattern(Base):
    __tablename__ = "workflow_patterns"
    __table_args__ = (UniqueConstraint("tenant_id", "pattern_key"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    name: Mapped[str] = mapped_column(String(255))
    pattern_key: Mapped[str] = mapped_column(String(255), index=True)
    occurrences: Mapped[int] = mapped_column(Integer, default=1)
    suggestion: Mapped[str | None] = mapped_column(Text, nullable=True)
    automation_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sample_evidence: Mapped[list | None] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class DependencyEdge(Base):
    __tablename__ = "dependency_edges"
    __table_args__ = (UniqueConstraint("tenant_id", "from_id", "to_id", "rel_type"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    from_type: Mapped[str] = mapped_column(String(64))
    from_id: Mapped[str] = mapped_column(String(255), index=True)
    to_type: Mapped[str] = mapped_column(String(64))
    to_id: Mapped[str] = mapped_column(String(255), index=True)
    rel_type: Mapped[str] = mapped_column(String(64), default="depends_on")
    criticality: Mapped[float] = mapped_column(Float, default=0.5)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Opportunity(Base):
    __tablename__ = "opportunities"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    category: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(512))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    score: Mapped[float] = mapped_column(Float, default=0.5)
    evidence: Mapped[list | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    category: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(512))
    action: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(32), default="medium")
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    related_refs: Mapped[list | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="proposed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ResearchReport(Base):
    __tablename__ = "research_reports"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    problem: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="completed")
    evidence: Mapped[list | None] = mapped_column(JSON, nullable=True)
    patterns: Mapped[list | None] = mapped_column(JSON, nullable=True)
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendations: Mapped[list | None] = mapped_column(JSON, nullable=True)
    executive_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EntityRecord(Base):
    """Canonical person/project entity for resolution within a tenant."""

    __tablename__ = "entity_records"
    __table_args__ = (UniqueConstraint("tenant_id", "entity_type", "canonical_key"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    entity_type: Mapped[str] = mapped_column(String(32), index=True)  # person | project
    canonical_key: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(255))
    aliases: Mapped[list | None] = mapped_column(JSON, nullable=True)
    merged_into_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("entity_records.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EntityMergeAudit(Base):
    __tablename__ = "entity_merge_audits"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    source_entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("entity_records.id"))
    target_entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("entity_records.id"))
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PendingMemoryLink(Base):
    __tablename__ = "pending_memory_links"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    link_type: Mapped[str] = mapped_column(String(64))  # decision|project
    target_id: Mapped[str] = mapped_column(String(255))
    source_ref: Mapped[str] = mapped_column(String(255))
    source_system: Mapped[str | None] = mapped_column(String(64), nullable=True)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    status: Mapped[str] = mapped_column(String(32), default="proposed")  # proposed|confirmed|rejected
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)


class TenantCryptoKey(Base):
    """Envelope encryption key registry (DEK wrapped by app secret / KMS placeholder)."""

    __tablename__ = "tenant_crypto_keys"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    wrapped_dek: Mapped[str] = mapped_column(Text)
    algorithm: Mapped[str] = mapped_column(String(64), default="aes-256-gcm")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ProjectMembership(Base):
    __tablename__ = "project_memberships"
    __table_args__ = (UniqueConstraint("project_id", "user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(32), default="member")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    """Append-only security/compliance audit trail (no updates in application code)."""

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    actor_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    action: Mapped[str] = mapped_column(String(64), index=True)
    resource_type: Mapped[str] = mapped_column(String(64))
    resource_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LegalHold(Base):
    __tablename__ = "legal_holds"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    name: Mapped[str] = mapped_column(String(255))
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RetentionPolicy(Base):
    __tablename__ = "retention_policies"
    __table_args__ = (UniqueConstraint("tenant_id", "resource_type"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    resource_type: Mapped[str] = mapped_column(String(64), default="document")
    retain_days: Mapped[int] = mapped_column(Integer, default=365)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TenantLlmQuota(Base):
    """Per-tenant daily LLM token budget and preferred model route."""

    __tablename__ = "tenant_llm_quotas"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    daily_token_limit: Mapped[int] = mapped_column(Integer, default=100_000)
    tokens_used_today: Mapped[int] = mapped_column(Integer, default=0)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    model_route: Mapped[str | None] = mapped_column(String(128), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class LlmUsageEvent(Base):
    __tablename__ = "llm_usage_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    task: Mapped[str] = mapped_column(String(32), default="chat")
    model: Mapped[str] = mapped_column(String(128), default="")
    tokens: Mapped[int] = mapped_column(Integer, default=0)
    cached: Mapped[bool] = mapped_column(Boolean, default=False)
    blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BackupDrill(Base):
    """Recorded backup/restore drills for RPO/RTO evidence."""

    __tablename__ = "backup_drills"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    environment: Mapped[str] = mapped_column(String(32), default="staging")
    store: Mapped[str] = mapped_column(String(32))  # postgres | neo4j | qdrant | object
    rpo_hours: Mapped[float] = mapped_column(Float, default=24.0)
    rto_hours: Mapped[float] = mapped_column(Float, default=4.0)
    status: Mapped[str] = mapped_column(String(32), default="passed")  # passed | failed | skipped
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    performed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    performed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DeployProof(Base):
    """Evidence that a deploy mode (saas / single-tenant / private VPC) was exercised."""

    __tablename__ = "deploy_proofs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    deploy_mode: Mapped[str] = mapped_column(String(32), index=True)
    environment: Mapped[str] = mapped_column(String(32), default="staging")
    status: Mapped[str] = mapped_column(String(32), default="proven")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    proven_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    proven_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ChaosTest(Base):
    __tablename__ = "chaos_tests"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    component: Mapped[str] = mapped_column(String(64))
    environment: Mapped[str] = mapped_column(String(32), default="staging")
    status: Mapped[str] = mapped_column(String(32), default="passed")
    steps: Mapped[list | None] = mapped_column(JSON, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    performed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    performed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ExpertFeedback(Base):
    """Labeled feedback for expert ranking calibration."""

    __tablename__ = "expert_feedback"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    person_key: Mapped[str] = mapped_column(String(255), index=True)
    topic: Mapped[str | None] = mapped_column(String(255), nullable=True)
    label: Mapped[int] = mapped_column(Integer, default=1)  # 1 helpful, 0 not, -1 wrong
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ModelEvalRun(Base):
    """Offline eval / backtest reports for risk & forecast models."""

    __tablename__ = "model_eval_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    model_name: Mapped[str] = mapped_column(String(64), index=True)
    metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    agent_type: Mapped[str] = mapped_column(String(32), default="research")  # research | ops
    problem: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="completed")
    tools_used: Mapped[list | None] = mapped_column(JSON, nullable=True)
    citations: Mapped[list | None] = mapped_column(JSON, nullable=True)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    unsafe_attempted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AgentApproval(Base):
    """Human-in-the-loop gate for write/automation agent actions."""

    __tablename__ = "agent_approvals"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    agent_run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("agent_runs.id"), nullable=True)
    action_type: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending|approved|rejected
    requested_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    decided_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AutomationAction(Base):
    __tablename__ = "automation_actions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    pattern: Mapped[str] = mapped_column(String(64))  # notify | create_ticket | update_doc_draft
    title: Mapped[str] = mapped_column(String(512))
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="queued")  # queued|executed|blocked|failed
    policy_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class KpiDefinition(Base):
    __tablename__ = "kpi_definitions"
    __table_args__ = (UniqueConstraint("tenant_id", "key"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    key: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    unit: Mapped[str] = mapped_column(String(32), default="count")
    target: Mapped[float | None] = mapped_column(Float, nullable=True)
    audience: Mapped[str] = mapped_column(String(32), default="executive")  # executive | operator | both
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class KpiSnapshot(Base):
    __tablename__ = "kpi_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    kpi_key: Mapped[str] = mapped_column(String(64), index=True)
    value: Mapped[float] = mapped_column(Float, default=0.0)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EvalGateRun(Base):
    __tablename__ = "eval_gate_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    suite: Mapped[str] = mapped_column(String(64), default="rag")  # rag | agent | perf
    metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    environment: Mapped[str] = mapped_column(String(32), default="ci")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ComplianceControl(Base):
    __tablename__ = "compliance_controls"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    framework: Mapped[str] = mapped_column(String(32), default="soc2")  # soc2 | gdpr | pentest
    control_id: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default="implemented")  # implemented|partial|planned|accepted_risk
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner: Mapped[str | None] = mapped_column(String(128), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PenTestFinding(Base):
    __tablename__ = "pentest_findings"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255))
    severity: Mapped[str] = mapped_column(String(16), default="medium")
    status: Mapped[str] = mapped_column(String(32), default="open")  # open|remediated|accepted
    owner: Mapped[str | None] = mapped_column(String(128), nullable=True)
    remediation: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TenantBilling(Base):
    __tablename__ = "tenant_billing"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    plan: Mapped[str] = mapped_column(String(32), default="pilot")  # pilot|growth|enterprise
    seat_limit: Mapped[int] = mapped_column(Integer, default=25)
    document_limit: Mapped[int] = mapped_column(Integer, default=10_000)
    monthly_llm_token_limit: Mapped[int] = mapped_column(Integer, default=1_000_000)
    status: Mapped[str] = mapped_column(String(32), default="active")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SlaMeasurement(Base):
    __tablename__ = "sla_measurements"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    uptime_ratio: Mapped[float] = mapped_column(Float, default=1.0)
    search_p95_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    chat_p95_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    met_commitment: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
