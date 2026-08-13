"""Phase 8: GA maturity — ML eval, agents, automation, KPIs, compliance, billing

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "expert_feedback",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("person_key", sa.String(255), nullable=False),
        sa.Column("topic", sa.String(255)),
        sa.Column("label", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_expert_feedback_tenant_id", "expert_feedback", ["tenant_id"])
    op.create_index("ix_expert_feedback_person_key", "expert_feedback", ["person_key"])

    op.create_table(
        "model_eval_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("model_name", sa.String(64), nullable=False),
        sa.Column("metrics", sa.JSON()),
        sa.Column("passed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_model_eval_runs_tenant_id", "model_eval_runs", ["tenant_id"])
    op.create_index("ix_model_eval_runs_model_name", "model_eval_runs", ["model_name"])

    op.create_table(
        "agent_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("agent_type", sa.String(32), nullable=False, server_default="research"),
        sa.Column("problem", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="completed"),
        sa.Column("tools_used", sa.JSON()),
        sa.Column("citations", sa.JSON()),
        sa.Column("result", sa.JSON()),
        sa.Column("unsafe_attempted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_agent_runs_tenant_id", "agent_runs", ["tenant_id"])

    op.create_table(
        "agent_approvals",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("agent_run_id", sa.Uuid(), sa.ForeignKey("agent_runs.id")),
        sa.Column("action_type", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON()),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("requested_by", sa.Uuid(), sa.ForeignKey("users.id")),
        sa.Column("decided_by", sa.Uuid(), sa.ForeignKey("users.id")),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_agent_approvals_tenant_id", "agent_approvals", ["tenant_id"])

    op.create_table(
        "automation_actions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("pattern", sa.String(64), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("payload", sa.JSON()),
        sa.Column("status", sa.String(32), nullable=False, server_default="queued"),
        sa.Column("policy_reason", sa.String(255)),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("executed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_automation_actions_tenant_id", "automation_actions", ["tenant_id"])

    op.create_table(
        "kpi_definitions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("key", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("unit", sa.String(32), nullable=False, server_default="count"),
        sa.Column("target", sa.Float()),
        sa.Column("audience", sa.String(32), nullable=False, server_default="executive"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("tenant_id", "key"),
    )
    op.create_index("ix_kpi_definitions_tenant_id", "kpi_definitions", ["tenant_id"])

    op.create_table(
        "kpi_snapshots",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("kpi_key", sa.String(64), nullable=False),
        sa.Column("value", sa.Float(), nullable=False, server_default="0"),
        sa.Column("captured_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_kpi_snapshots_tenant_id", "kpi_snapshots", ["tenant_id"])
    op.create_index("ix_kpi_snapshots_kpi_key", "kpi_snapshots", ["kpi_key"])

    op.create_table(
        "eval_gate_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("suite", sa.String(64), nullable=False, server_default="rag"),
        sa.Column("metrics", sa.JSON()),
        sa.Column("passed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("environment", sa.String(32), nullable=False, server_default="ci"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "compliance_controls",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("framework", sa.String(32), nullable=False, server_default="soc2"),
        sa.Column("control_id", sa.String(64), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="implemented"),
        sa.Column("evidence", sa.Text()),
        sa.Column("owner", sa.String(128)),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_compliance_controls_control_id", "compliance_controls", ["control_id"])

    op.create_table(
        "pentest_findings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(32), nullable=False, server_default="open"),
        sa.Column("owner", sa.String(128)),
        sa.Column("remediation", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "tenant_billing",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("plan", sa.String(32), nullable=False, server_default="pilot"),
        sa.Column("seat_limit", sa.Integer(), nullable=False, server_default="25"),
        sa.Column("document_limit", sa.Integer(), nullable=False, server_default="10000"),
        sa.Column("monthly_llm_token_limit", sa.Integer(), nullable=False, server_default="1000000"),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("tenant_id"),
    )
    op.create_index("ix_tenant_billing_tenant_id", "tenant_billing", ["tenant_id"])

    op.create_table(
        "sla_measurements",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("uptime_ratio", sa.Float(), nullable=False, server_default="1"),
        sa.Column("search_p95_ms", sa.Float()),
        sa.Column("chat_p95_ms", sa.Float()),
        sa.Column("met_commitment", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_sla_measurements_tenant_id", "sla_measurements", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("sla_measurements")
    op.drop_table("tenant_billing")
    op.drop_table("pentest_findings")
    op.drop_table("compliance_controls")
    op.drop_table("eval_gate_runs")
    op.drop_table("kpi_snapshots")
    op.drop_table("kpi_definitions")
    op.drop_table("automation_actions")
    op.drop_table("agent_approvals")
    op.drop_table("agent_runs")
    op.drop_table("model_eval_runs")
    op.drop_table("expert_feedback")
