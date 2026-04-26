"""add origin to author_dedup_conflicts and entity_dedup_conflicts

Revision ID: 20260426_0005
Revises: 20260426_0004
Create Date: 2026-04-26 16:00:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op  # pylint: disable=no-name-in-module

revision = "20260426_0005"
down_revision = "20260426_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "author_dedup_conflicts",
        sa.Column("origin", sa.String(length=32), nullable=False, server_default="scan"),
    )
    op.create_index(
        "ix_author_dedup_conflicts_origin",
        "author_dedup_conflicts",
        ["origin"],
        unique=False,
    )
    op.add_column(
        "entity_dedup_conflicts",
        sa.Column("origin", sa.String(length=32), nullable=False, server_default="scan"),
    )
    op.create_index(
        "ix_entity_dedup_conflicts_origin",
        "entity_dedup_conflicts",
        ["origin"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_entity_dedup_conflicts_origin", table_name="entity_dedup_conflicts")
    op.drop_column("entity_dedup_conflicts", "origin")
    op.drop_index("ix_author_dedup_conflicts_origin", table_name="author_dedup_conflicts")
    op.drop_column("author_dedup_conflicts", "origin")
