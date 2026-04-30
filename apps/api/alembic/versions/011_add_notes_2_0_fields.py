"""add notes 2.0 fields

Revision ID: 011_add_notes_2_0_fields
Revises: 010_add_upload_sessions_table
Create Date: 2026-04-27
"""

from alembic import op
import sqlalchemy as sa


revision = "011_add_notes_2_0_fields"
down_revision = "010_add_upload_sessions_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("notes", sa.Column("content_doc", sa.JSON(), nullable=True))
    op.add_column("notes", sa.Column("linked_evidence", sa.JSON(), nullable=True))
    op.add_column(
        "notes",
        sa.Column(
            "source_type",
            sa.String(length=32),
            nullable=False,
            server_default="manual",
        ),
    )


def downgrade() -> None:
    op.drop_column("notes", "source_type")
    op.drop_column("notes", "linked_evidence")
    op.drop_column("notes", "content_doc")
