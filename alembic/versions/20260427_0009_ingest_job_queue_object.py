"""ingest_jobs queued source object metadata for S3/MinIO queue

Revision ID: 20260427_0009
Revises: 20260427_0008
Create Date: 2026-04-27
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op  # pylint: disable=no-name-in-module

revision = "20260427_0009"
down_revision = "20260427_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ingest_jobs",
        sa.Column("queued_source_object_key", sa.Text(), nullable=True),
    )
    op.add_column(
        "ingest_jobs",
        sa.Column("queued_source_size", sa.Integer(), nullable=True),
    )
    op.add_column(
        "ingest_jobs",
        sa.Column("queued_source_etag", sa.String(length=128), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ingest_jobs", "queued_source_etag")
    op.drop_column("ingest_jobs", "queued_source_size")
    op.drop_column("ingest_jobs", "queued_source_object_key")
