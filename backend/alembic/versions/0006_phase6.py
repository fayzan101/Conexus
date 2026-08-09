"""Phase 6: ABAC attrs, audit, retention, SCIM, legal hold

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("scim_external_id", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("region", sa.String(64), nullable=True))
    op.add_column("users", sa.Column("clearance", sa.String(32), server_default="internal", nullable=False))
    op.create_index("ix_users_scim_external_id", "users", ["scim_external_id"])

    op.add_column("documents", sa.Column("classification", sa.String(32), server_default="internal", nullable=False))
    op.add_column("documents", sa.Column("region", sa.String(64), nullable=True))
    op.add_column("documents", sa.Column("legal_hold", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column("documents", sa.Column("retain_until", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "project_memberships",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("project_id", "user_id"),
    )
    op.create_index("ix_project_memberships_tenant_id", "project_memberships", ["tenant_id"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("actor_id", sa.Uuid()),
        sa.Column("actor_email", sa.String(320)),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.String(255)),
        sa.Column("detail", sa.JSON()),
        sa.Column("request_id", sa.String(64)),
        sa.Column("ip_address", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_audit_logs_tenant_id", "audit_logs", ["tenant_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])

    op.create_table(
        "legal_holds",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("reason", sa.Text()),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_legal_holds_tenant_id", "legal_holds", ["tenant_id"])

    op.create_table(
        "retention_policies",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=False),
        sa.Column("retain_days", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("tenant_id", "resource_type"),
    )
    op.create_index("ix_retention_policies_tenant_id", "retention_policies", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("retention_policies")
    op.drop_table("legal_holds")
    op.drop_table("audit_logs")
    op.drop_table("project_memberships")
    op.drop_column("documents", "retain_until")
    op.drop_column("documents", "legal_hold")
    op.drop_column("documents", "region")
    op.drop_column("documents", "classification")
    op.drop_index("ix_users_scim_external_id", table_name="users")
    op.drop_column("users", "clearance")
    op.drop_column("users", "region")
    op.drop_column("users", "scim_external_id")
