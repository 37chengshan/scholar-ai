"""add processing task reliability fields

Revision ID: 013_add_processing_task_reliability_fields
Revises: 012_add_paper_reading_card_doc
Create Date: 2026-04-29
"""

from alembic import op
import sqlalchemy as sa


revision = "013_add_processing_task_reliability_fields"
down_revision = "012_add_paper_reading_card_doc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "processing_tasks",
        sa.Column(
            "task_type",
            sa.String(length=50),
            nullable=False,
            server_default="pdf_processing",
        ),
    )
    op.add_column(
        "processing_tasks",
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "processing_tasks",
        sa.Column("cancellation_reason", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "processing_tasks",
        sa.Column("retry_trace_id", sa.String(length=36), nullable=True),
    )
    op.add_column(
        "processing_tasks",
        sa.Column("cost_breakdown", sa.JSON(), nullable=True),
    )
    op.add_column(
        "processing_tasks",
        sa.Column("cache_stats", sa.JSON(), nullable=True),
    )
    op.add_column(
        "processing_tasks",
        sa.Column("queue_wait_ms", sa.Integer(), nullable=True),
    )

    op.create_index(
        "idx_processing_tasks_task_type",
        "processing_tasks",
        ["task_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_processing_tasks_task_type", table_name="processing_tasks")
    op.drop_column("processing_tasks", "queue_wait_ms")
    op.drop_column("processing_tasks", "cache_stats")
    op.drop_column("processing_tasks", "cost_breakdown")
    op.drop_column("processing_tasks", "retry_trace_id")
    op.drop_column("processing_tasks", "cancellation_reason")
    op.drop_column("processing_tasks", "cancelled_at")
    op.drop_column("processing_tasks", "task_type")
