"""Phase 5: multi-tenant isolation, entity resolution, memory links, FTS field

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_tenant(table: str) -> None:
    op.add_column(table, sa.Column("tenant_id", sa.String(64), server_default="default", nullable=False))
    op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])


def upgrade() -> None:
    for table in [
        "users",
        "invite_tokens",
        "projects",
        "documents",
        "meetings",
        "ingest_jobs",
        "decisions",
        "query_logs",
        "connector_accounts",
    ]:
        _add_tenant(table)

    op.add_column("documents", sa.Column("search_vector", sa.Text(), nullable=True))

    # Relax global uniques in favor of tenant-scoped (best-effort; SQLite may no-op drop)
    try:
        op.drop_constraint("users_email_key", "users", type_="unique")
    except Exception:
        pass
    try:
        op.drop_index("ix_users_idp_subject", table_name="users")
    except Exception:
        pass
    op.create_index("ix_users_idp_subject", "users", ["idp_subject"], unique=False)
    op.create_unique_constraint("uq_users_tenant_email", "users", ["tenant_id", "email"])

    try:
        op.drop_constraint("projects_name_key", "projects", type_="unique")
    except Exception:
        pass
    op.create_unique_constraint("uq_projects_tenant_name", "projects", ["tenant_id", "name"])

    try:
        op.drop_constraint("connector_accounts_provider_external_account_id_key", "connector_accounts", type_="unique")
    except Exception:
        pass
    op.create_unique_constraint(
        "uq_connector_accounts_tenant_provider_ext",
        "connector_accounts",
        ["tenant_id", "provider", "external_account_id"],
    )

    op.create_table(
        "entity_records",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("entity_type", sa.String(32), nullable=False),
        sa.Column("canonical_key", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("aliases", sa.JSON()),
        sa.Column("merged_into_id", sa.Uuid(), sa.ForeignKey("entity_records.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("tenant_id", "entity_type", "canonical_key"),
    )
    op.create_index("ix_entity_records_tenant_id", "entity_records", ["tenant_id"])
    op.create_index("ix_entity_records_entity_type", "entity_records", ["entity_type"])

    op.create_table(
        "entity_merge_audits",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("source_entity_id", sa.Uuid(), sa.ForeignKey("entity_records.id"), nullable=False),
        sa.Column("target_entity_id", sa.Uuid(), sa.ForeignKey("entity_records.id"), nullable=False),
        sa.Column("reason", sa.Text()),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_entity_merge_audits_tenant_id", "entity_merge_audits", ["tenant_id"])

    op.create_table(
        "pending_memory_links",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("link_type", sa.String(64), nullable=False),
        sa.Column("target_id", sa.String(255), nullable=False),
        sa.Column("source_ref", sa.String(255), nullable=False),
        sa.Column("source_system", sa.String(64)),
        sa.Column("title", sa.String(512)),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("rationale", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("reviewed_by", sa.Uuid(), sa.ForeignKey("users.id")),
    )
    op.create_index("ix_pending_memory_links_tenant_id", "pending_memory_links", ["tenant_id"])

    op.create_table(
        "tenant_crypto_keys",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False, unique=True),
        sa.Column("wrapped_dek", sa.Text(), nullable=False),
        sa.Column("algorithm", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("rotated_at", sa.DateTime(timezone=True)),
    )


def downgrade() -> None:
    op.drop_table("tenant_crypto_keys")
    op.drop_table("pending_memory_links")
    op.drop_table("entity_merge_audits")
    op.drop_table("entity_records")
    op.drop_column("documents", "search_vector")
    for table in [
        "connector_accounts",
        "query_logs",
        "decisions",
        "ingest_jobs",
        "meetings",
        "documents",
        "projects",
        "invite_tokens",
        "users",
    ]:
        op.drop_index(f"ix_{table}_tenant_id", table_name=table)
        op.drop_column(table, "tenant_id")
