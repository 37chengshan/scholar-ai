"""add notes generation tasks table

Revision ID: 004_add_notes_generation_tasks
Revises: 003_add_paper_substatus_fields
Create Date: 2026-04-13

This migration creates the notes_generation_tasks table for async notes
generation with claim lock mechanism.

Per Review Fix #9: Notes异步化 + 抢占锁

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "004_add_notes_generation_tasks"
down_revision = "003_add_paper_substatus_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create notes_generation_tasks table."""
    op.create_table(
        "notes_generation_tasks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("paper_id", sa.String(36), sa.ForeignKey("papers.id"), unique=True, nullable=False),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("claimed_by", sa.String(50), nullable=True),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.String(500), nullable=True),
        sa.Column("attempts", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 创建索引
    op.create_index("idx_notes_tasks_status", "notes_generation_tasks", ["status"])
    op.create_index("idx_notes_tasks_paper_id", "notes_generation_tasks", ["paper_id"])


def downgrade() -> None:
    """Remove notes_generation_tasks table."""
    op.drop_index("idx_notes_tasks_paper_id", table_name="notes_generation_tasks")
    op.drop_index("idx_notes_tasks_status", table_name="notes_generation_tasks")
    op.drop_table("notes_generation_tasks")