"""workspace_hypotheses table for BT10 persistence

Revision ID: 20260426_0006
Revises: 20260426_0005
Create Date: 2026-04-26 18:00:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op  # pylint: disable=no-name-in-module

revision = "20260426_0006"
down_revision = "20260426_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workspace_hypotheses",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=128), nullable=False, index=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_workspace_hypotheses_workspace_created",
        "workspace_hypotheses",
        ["workspace_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_workspace_hypotheses_workspace_created", table_name="workspace_hypotheses")
    op.drop_table("workspace_hypotheses")
