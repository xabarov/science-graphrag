"""add ingest job stages table

Revision ID: 20260425_0002
Revises: 20260424_0001
Create Date: 2026-04-25 14:45:00
"""

from __future__ import annotations

from alembic import op  # pylint: disable=no-name-in-module
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260425_0002"
down_revision = "20260424_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ingest_job_stages",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("stage", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metrics_json", sa.Text(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", "stage", name="uq_ingest_job_stage"),
    )
    op.create_index(
        "ix_ingest_job_stages_job_id",
        "ingest_job_stages",
        ["job_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_ingest_job_stages_job_id", table_name="ingest_job_stages")
    op.drop_table("ingest_job_stages")
