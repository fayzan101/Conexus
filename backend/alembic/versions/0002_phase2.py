"""Phase 2 tables: connectors, decision links, timeline, expertise, freshness

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-05
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("decisions", sa.Column("supersedes_id", sa.Uuid(), sa.ForeignKey("decisions.id")))

    op.create_table(
        "connector_accounts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("external_account_id", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255)),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("credentials", sa.JSON()),
        sa.Column("cursor", sa.String(512)),
        sa.Column("last_sync_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("provider", "external_account_id"),
    )
    op.create_index("ix_connector_accounts_provider", "connector_accounts", ["provider"])

    op.create_table(
        "decision_links",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("decision_id", sa.Uuid(), sa.ForeignKey("decisions.id", ondelete="CASCADE")),
        sa.Column("link_type", sa.String(64), nullable=False),
        sa.Column("target_id", sa.String(255), nullable=False),
        sa.Column("target_title", sa.String(512)),
        sa.Column("source_system", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "timeline_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("summary", sa.Text()),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id")),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_system", sa.String(64)),
        sa.Column("source_ref", sa.String(255)),
        sa.Column("metadata_json", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_timeline_events_event_type", "timeline_events", ["event_type"])
    op.create_index("ix_timeline_events_occurred_at", "timeline_events", ["occurred_at"])

    op.create_table(
        "expertise_signals",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("person_key", sa.String(255), nullable=False),
        sa.Column("topic", sa.String(255), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("evidence", sa.Text()),
        sa.Column("source_system", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_expertise_signals_person_key", "expertise_signals", ["person_key"])
    op.create_index("ix_expertise_signals_topic", "expertise_signals", ["topic"])

    op.create_table(
        "knowledge_scores",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.String(255), nullable=False),
        sa.Column("freshness", sa.Float(), nullable=False),
        sa.Column("trust", sa.Float(), nullable=False),
        sa.Column("completeness", sa.Float(), nullable=False),
        sa.Column("risk", sa.Float(), nullable=False),
        sa.Column("ownership", sa.String(255)),
        sa.Column("duplicate_likelihood", sa.Float(), nullable=False),
        sa.Column("suggested_update", sa.Text()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_knowledge_scores_entity_type", "knowledge_scores", ["entity_type"])
    op.create_index("ix_knowledge_scores_entity_id", "knowledge_scores", ["entity_id"])


def downgrade() -> None:
    op.drop_table("knowledge_scores")
    op.drop_table("expertise_signals")
    op.drop_table("timeline_events")
    op.drop_table("decision_links")
    op.drop_table("connector_accounts")
    op.drop_column("decisions", "supersedes_id")
