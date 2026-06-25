"""create moodboard tables

Brief sessions, generation requests, and moodboards for the agentic moodboard API.

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-24 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "brief_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("state", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_brief_sessions_owner", "brief_sessions", ["owner"])

    op.create_table(
        "generation_requests",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner", sa.String(length=255), nullable=False),
        sa.Column("brief_id", sa.String(length=36), nullable=True),
        sa.Column("input", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_generation_requests_owner", "generation_requests", ["owner"])

    op.create_table(
        "moodboards",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("request_id", sa.String(length=36), nullable=False),
        sa.Column("owner", sa.String(length=255), nullable=False),
        sa.Column("direction_name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("concept", sa.JSON(), nullable=True),
        sa.Column("palette", sa.JSON(), nullable=True),
        sa.Column("images", sa.JSON(), nullable=True),
        sa.Column("html", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_moodboards_owner", "moodboards", ["owner"])
    op.create_index("ix_moodboards_request_id", "moodboards", ["request_id"])


def downgrade() -> None:
    op.drop_index("ix_moodboards_request_id", table_name="moodboards")
    op.drop_index("ix_moodboards_owner", table_name="moodboards")
    op.drop_table("moodboards")
    op.drop_index("ix_generation_requests_owner", table_name="generation_requests")
    op.drop_table("generation_requests")
    op.drop_index("ix_brief_sessions_owner", table_name="brief_sessions")
    op.drop_table("brief_sessions")
