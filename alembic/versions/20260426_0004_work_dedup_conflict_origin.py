"""add origin to work_dedup_conflicts (ingest vs scan)

Revision ID: 20260426_0004
Revises: 20260425_0003
Create Date: 2026-04-26 12:00:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op  # pylint: disable=no-name-in-module

revision = "20260426_0004"
down_revision = "20260425_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "work_dedup_conflicts",
        sa.Column("origin", sa.String(length=32), nullable=False, server_default="scan"),
    )
    op.create_index(
        "ix_work_dedup_conflicts_origin",
        "work_dedup_conflicts",
        ["origin"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_work_dedup_conflicts_origin", table_name="work_dedup_conflicts")
    op.drop_column("work_dedup_conflicts", "origin")
