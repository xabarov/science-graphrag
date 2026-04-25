"""add phoenix trace id to ingest jobs

Revision ID: 20260425_0003
Revises: 20260425_0002
Create Date: 2026-04-25 15:45:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op  # pylint: disable=no-name-in-module

# revision identifiers, used by Alembic.
revision = "20260425_0003"
down_revision = "20260425_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ingest_jobs", sa.Column("phoenix_trace_id", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("ingest_jobs", "phoenix_trace_id")
