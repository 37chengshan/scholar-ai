"""add task checkpoint and trace fields

Revision ID: 002_add_task_checkpoint_and_trace
Revises: 001_add_knowledge_bases
Create Date: 2026-04-13

This migration adds checkpoint path ref, trace_id, stage_timings,
failure classification fields, and is_retryable boolean to processing_tasks.

Per Review Fix #3: checkpoint只存路径引用，不存大JSON
Per Review Fix #4: Boolean使用PostgreSQL原生Boolean
Per Review Fix #8: trace_id贯穿日志

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "002_add_task_checkpoint_and_trace"
down_revision = "001_add_knowledge_bases"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add checkpoint and trace fields to processing_tasks."""
    # Checkpoint路径引用（Per Review Fix #3）
    op.add_column(
        "processing_tasks",
        sa.Column("checkpoint_stage", sa.String(50), nullable=True),
    )
    op.add_column(
        "processing_tasks",
        sa.Column("checkpoint_storage_key", sa.String(255), nullable=True),
    )
    op.add_column(
        "processing_tasks",
        sa.Column("checkpoint_version", sa.Integer(), nullable=False, server_default="0"),
    )

    # 阶段耗时（JSON）
    op.add_column(
        "processing_tasks",
        sa.Column("stage_timings", sa.JSON(), nullable=True),
    )

    # 失败分类（统一 vocabulary）
    op.add_column(
        "processing_tasks",
        sa.Column("failure_stage", sa.String(20), nullable=True),
    )
    op.add_column(
        "processing_tasks",
        sa.Column("failure_code", sa.String(100), nullable=True),
    )
    op.add_column(
        "processing_tasks",
        sa.Column("failure_message", sa.Text(), nullable=True),
    )

    # 重试标记（PostgreSQL Boolean, Per Review Fix #4）
    op.add_column(
        "processing_tasks",
        sa.Column("is_retryable", sa.Boolean(), nullable=False, server_default="true"),
    )

    # trace_id（Per Review Fix #8）
    op.add_column(
        "processing_tasks",
        sa.Column("trace_id", sa.String(36), nullable=True),
    )

    # 创建索引
    op.create_index("idx_processing_tasks_trace_id", "processing_tasks", ["trace_id"])


def downgrade() -> None:
    """Remove checkpoint and trace fields from processing_tasks."""
    # 删除索引
    op.drop_index("idx_processing_tasks_trace_id", table_name="processing_tasks")

    # 删除列（逆序）
    op.drop_column("processing_tasks", "trace_id")
    op.drop_column("processing_tasks", "is_retryable")
    op.drop_column("processing_tasks", "failure_message")
    op.drop_column("processing_tasks", "failure_code")
    op.drop_column("processing_tasks", "failure_stage")
    op.drop_column("processing_tasks", "stage_timings")
    op.drop_column("processing_tasks", "checkpoint_version")
    op.drop_column("processing_tasks", "checkpoint_storage_key")
    op.drop_column("processing_tasks", "checkpoint_stage")