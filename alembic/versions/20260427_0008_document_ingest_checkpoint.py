"""documents.ingest_checkpoint_json for stage-safe ingest

Revision ID: 20260427_0008
Revises: 20260426_0007
Create Date: 2026-04-27 12:00:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op  # pylint: disable=no-name-in-module

revision = "20260427_0008"
down_revision = "20260426_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("ingest_checkpoint_json", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("documents", "ingest_checkpoint_json")
