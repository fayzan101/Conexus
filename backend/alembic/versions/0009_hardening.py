"""Production hardening: tenant_id on OS/chat tables

Revision ID: 0009
Revises: 0008
Create Date: 2026-08-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLES = [
    "chat_sessions",
    "timeline_events",
    "expertise_signals",
    "knowledge_scores",
    "predictions",
    "workflow_patterns",
    "dependency_edges",
    "opportunities",
    "recommendations",
    "research_reports",
]


def upgrade() -> None:
    for table in _TABLES:
        op.add_column(table, sa.Column("tenant_id", sa.String(64), server_default="default", nullable=False))
        op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])

    # workflow_patterns: replace global unique pattern_key with tenant-scoped unique
    try:
        op.drop_index("ix_workflow_patterns_pattern_key", table_name="workflow_patterns")
    except Exception:
        pass
    try:
        op.drop_constraint("workflow_patterns_pattern_key_key", "workflow_patterns", type_="unique")
    except Exception:
        pass
    op.create_index("ix_workflow_patterns_pattern_key", "workflow_patterns", ["pattern_key"])
    op.create_unique_constraint("uq_workflow_patterns_tenant_pattern", "workflow_patterns", ["tenant_id", "pattern_key"])

    # dependency_edges: replace unique with tenant-scoped
    try:
        op.drop_constraint("dependency_edges_from_id_to_id_rel_type_key", "dependency_edges", type_="unique")
    except Exception:
        pass
    op.create_unique_constraint(
        "uq_dependency_edges_tenant_edge",
        "dependency_edges",
        ["tenant_id", "from_id", "to_id", "rel_type"],
    )


def downgrade() -> None:
    try:
        op.drop_constraint("uq_dependency_edges_tenant_edge", "dependency_edges", type_="unique")
    except Exception:
        pass
    try:
        op.drop_constraint("uq_workflow_patterns_tenant_pattern", "workflow_patterns", type_="unique")
    except Exception:
        pass
    for table in reversed(_TABLES):
        op.drop_index(f"ix_{table}_tenant_id", table_name=table)
        op.drop_column(table, "tenant_id")
