"""Phase 3 tables: predictions, workflows, dependencies, opportunities, agents

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-05
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "predictions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("prediction_type", sa.String(64), nullable=False),
        sa.Column("subject_type", sa.String(64), nullable=False),
        sa.Column("subject_id", sa.String(255), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("probability", sa.Float(), nullable=False),
        sa.Column("severity", sa.String(32), nullable=False),
        sa.Column("rationale", sa.Text()),
        sa.Column("features", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_predictions_prediction_type", "predictions", ["prediction_type"])

    op.create_table(
        "workflow_patterns",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("pattern_key", sa.String(255), nullable=False),
        sa.Column("occurrences", sa.Integer(), nullable=False),
        sa.Column("suggestion", sa.Text()),
        sa.Column("automation_type", sa.String(64)),
        sa.Column("sample_evidence", sa.JSON()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("pattern_key"),
    )
    op.create_index("ix_workflow_patterns_pattern_key", "workflow_patterns", ["pattern_key"])

    op.create_table(
        "dependency_edges",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("from_type", sa.String(64), nullable=False),
        sa.Column("from_id", sa.String(255), nullable=False),
        sa.Column("to_type", sa.String(64), nullable=False),
        sa.Column("to_id", sa.String(255), nullable=False),
        sa.Column("rel_type", sa.String(64), nullable=False),
        sa.Column("criticality", sa.Float(), nullable=False),
        sa.Column("metadata_json", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("from_id", "to_id", "rel_type"),
    )
    op.create_index("ix_dependency_edges_from_id", "dependency_edges", ["from_id"])
    op.create_index("ix_dependency_edges_to_id", "dependency_edges", ["to_id"])

    op.create_table(
        "opportunities",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("evidence", sa.JSON()),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_opportunities_category", "opportunities", ["category"])

    op.create_table(
        "recommendations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(32), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("related_refs", sa.JSON()),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_recommendations_category", "recommendations", ["category"])

    op.create_table(
        "research_reports",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("problem", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("evidence", sa.JSON()),
        sa.Column("patterns", sa.JSON()),
        sa.Column("root_cause", sa.Text()),
        sa.Column("recommendations", sa.JSON()),
        sa.Column("executive_summary", sa.Text()),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("research_reports")
    op.drop_table("recommendations")
    op.drop_table("opportunities")
    op.drop_table("dependency_edges")
    op.drop_table("workflow_patterns")
    op.drop_table("predictions")
