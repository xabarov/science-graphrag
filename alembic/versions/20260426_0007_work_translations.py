"""work_translations table (LX2 persistence scaffold)

Revision ID: 20260426_0007
Revises: 20260426_0006
Create Date: 2026-04-26 22:00:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op  # pylint: disable=no-name-in-module

revision = "20260426_0007"
down_revision = "20260426_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "work_translations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("work_id", sa.String(length=256), nullable=False),
        sa.Column("locale", sa.String(length=32), nullable=False),
        sa.Column("field", sa.String(length=32), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("model", sa.String(length=256), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.UniqueConstraint("work_id", "locale", "field", name="uq_work_translation_key"),
    )
    op.create_index("ix_work_translations_work_id", "work_translations", ["work_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_work_translations_work_id", table_name="work_translations")
    op.drop_table("work_translations")
