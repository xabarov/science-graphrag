"""add persistent ingest and dedup job tables

Revision ID: 20260424_0001
Revises:
Create Date: 2026-04-24 23:30:00
"""

from __future__ import annotations

from alembic import op  # pylint: disable=no-name-in-module
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260424_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ingest_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=128), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("progress_current", sa.Integer(), nullable=False),
        sa.Column("progress_total", sa.Integer(), nullable=False),
        sa.Column("logs", sa.Text(), nullable=False),
        sa.Column("work_id", sa.String(length=256), nullable=True),
        sa.Column("document_id", sa.String(length=36), nullable=True),
        sa.Column("skipped_duplicate", sa.Boolean(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("parent_job_id", sa.String(length=36), nullable=True),
        sa.Column("child_job_ids_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id"),
    )
    op.create_index("ix_ingest_jobs_job_id", "ingest_jobs", ["job_id"], unique=True)
    op.create_index("ix_ingest_jobs_workspace_id", "ingest_jobs", ["workspace_id"], unique=False)
    op.create_index("ix_ingest_jobs_status", "ingest_jobs", ["status"], unique=False)

    op.create_table(
        "dedup_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=128), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("conflicts_inserted", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id"),
    )
    op.create_index("ix_dedup_jobs_job_id", "dedup_jobs", ["job_id"], unique=True)
    op.create_index("ix_dedup_jobs_workspace_id", "dedup_jobs", ["workspace_id"], unique=False)
    op.create_index("ix_dedup_jobs_kind", "dedup_jobs", ["kind"], unique=False)
    op.create_index("ix_dedup_jobs_status", "dedup_jobs", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_dedup_jobs_status", table_name="dedup_jobs")
    op.drop_index("ix_dedup_jobs_kind", table_name="dedup_jobs")
    op.drop_index("ix_dedup_jobs_workspace_id", table_name="dedup_jobs")
    op.drop_index("ix_dedup_jobs_job_id", table_name="dedup_jobs")
    op.drop_table("dedup_jobs")

    op.drop_index("ix_ingest_jobs_status", table_name="ingest_jobs")
    op.drop_index("ix_ingest_jobs_workspace_id", table_name="ingest_jobs")
    op.drop_index("ix_ingest_jobs_job_id", table_name="ingest_jobs")
    op.drop_table("ingest_jobs")
