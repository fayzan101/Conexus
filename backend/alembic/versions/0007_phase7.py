"""Phase 7: LLM quotas, backup drills, deploy proofs, chaos tests

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-12
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tenant_llm_quotas",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("daily_token_limit", sa.Integer(), nullable=False, server_default="100000"),
        sa.Column("tokens_used_today", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("window_start", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("model_route", sa.String(128)),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("tenant_id"),
    )
    op.create_index("ix_tenant_llm_quotas_tenant_id", "tenant_llm_quotas", ["tenant_id"])

    op.create_table(
        "llm_usage_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("task", sa.String(32), nullable=False, server_default="chat"),
        sa.Column("model", sa.String(128), nullable=False, server_default=""),
        sa.Column("tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cached", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("blocked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_llm_usage_events_tenant_id", "llm_usage_events", ["tenant_id"])

    op.create_table(
        "backup_drills",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("environment", sa.String(32), nullable=False, server_default="staging"),
        sa.Column("store", sa.String(32), nullable=False),
        sa.Column("rpo_hours", sa.Float(), nullable=False, server_default="24"),
        sa.Column("rto_hours", sa.Float(), nullable=False, server_default="4"),
        sa.Column("status", sa.String(32), nullable=False, server_default="passed"),
        sa.Column("notes", sa.Text()),
        sa.Column("performed_by", sa.Uuid(), sa.ForeignKey("users.id")),
        sa.Column("performed_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_backup_drills_tenant_id", "backup_drills", ["tenant_id"])

    op.create_table(
        "deploy_proofs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("deploy_mode", sa.String(32), nullable=False),
        sa.Column("environment", sa.String(32), nullable=False, server_default="staging"),
        sa.Column("status", sa.String(32), nullable=False, server_default="proven"),
        sa.Column("notes", sa.Text()),
        sa.Column("proven_by", sa.Uuid(), sa.ForeignKey("users.id")),
        sa.Column("proven_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_deploy_proofs_deploy_mode", "deploy_proofs", ["deploy_mode"])

    op.create_table(
        "chaos_tests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("component", sa.String(64), nullable=False),
        sa.Column("environment", sa.String(32), nullable=False, server_default="staging"),
        sa.Column("status", sa.String(32), nullable=False, server_default="passed"),
        sa.Column("steps", sa.JSON()),
        sa.Column("notes", sa.Text()),
        sa.Column("performed_by", sa.Uuid(), sa.ForeignKey("users.id")),
        sa.Column("performed_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("chaos_tests")
    op.drop_index("ix_deploy_proofs_deploy_mode", table_name="deploy_proofs")
    op.drop_table("deploy_proofs")
    op.drop_index("ix_backup_drills_tenant_id", table_name="backup_drills")
    op.drop_table("backup_drills")
    op.drop_index("ix_llm_usage_events_tenant_id", table_name="llm_usage_events")
    op.drop_table("llm_usage_events")
    op.drop_index("ix_tenant_llm_quotas_tenant_id", table_name="tenant_llm_quotas")
    op.drop_table("tenant_llm_quotas")
