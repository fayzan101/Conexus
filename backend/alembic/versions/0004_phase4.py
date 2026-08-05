"""Phase 4: pilot hardening columns + invite tokens

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-05
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("idp_subject", sa.String(255), nullable=True))
    op.create_index("ix_users_idp_subject", "users", ["idp_subject"], unique=True)

    op.create_table(
        "invite_tokens",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("token_hash", sa.String(128), nullable=False),
        sa.Column("invited_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_invite_tokens_email", "invite_tokens", ["email"])
    op.create_index("ix_invite_tokens_token_hash", "invite_tokens", ["token_hash"], unique=True)

    op.add_column("ingest_jobs", sa.Column("attempts", sa.Integer(), server_default="0", nullable=False))
    op.add_column("ingest_jobs", sa.Column("max_attempts", sa.Integer(), server_default="3", nullable=False))
    op.add_column(
        "ingest_jobs", sa.Column("dead_lettered", sa.Boolean(), server_default=sa.text("false"), nullable=False)
    )
    op.add_column("ingest_jobs", sa.Column("queued_at", sa.DateTime(timezone=True), nullable=True))

    op.add_column("connector_accounts", sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("connector_accounts", sa.Column("health_ok", sa.Boolean(), nullable=True))
    op.add_column("connector_accounts", sa.Column("health_detail", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("connector_accounts", "health_detail")
    op.drop_column("connector_accounts", "health_ok")
    op.drop_column("connector_accounts", "token_expires_at")
    op.drop_column("ingest_jobs", "queued_at")
    op.drop_column("ingest_jobs", "dead_lettered")
    op.drop_column("ingest_jobs", "max_attempts")
    op.drop_column("ingest_jobs", "attempts")
    op.drop_index("ix_invite_tokens_token_hash", table_name="invite_tokens")
    op.drop_index("ix_invite_tokens_email", table_name="invite_tokens")
    op.drop_table("invite_tokens")
    op.drop_index("ix_users_idp_subject", table_name="users")
    op.drop_column("users", "idp_subject")
