"""add paper substatus fields

Revision ID: 003_add_paper_substatus_fields
Revises: 002_add_task_checkpoint_and_trace
Create Date: 2026-04-13

This migration adds sub-status Boolean fields to papers table for
granular pipeline tracking per Section 2 semantics:

- isSearchReady: PostgreSQL + Milvus text chunks ready
- isMultimodalReady: Milvus images/tables embedded
- isNotesReady: reading_notes populated
- notesFailed: Notes generation failed
- multimodalFailed: Multimodal embedding failed
- traceId: Trace ID from task (for log correlation)

Per Review Fix #4: Boolean 使用 PostgreSQL 原生 Boolean
Per Review Fix #8: trace_id 贯穿日志

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "003_add_paper_substatus_fields"
down_revision = "002_add_task_checkpoint_and_trace"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add sub-status fields to papers table."""
    # 子状态（PostgreSQL Boolean, Per Review Fix #4）
    op.add_column(
        "papers",
        sa.Column("isSearchReady", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "papers",
        sa.Column("isMultimodalReady", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "papers",
        sa.Column("isNotesReady", sa.Boolean(), nullable=False, server_default="false"),
    )

    # 失败标记
    op.add_column(
        "papers",
        sa.Column("notesFailed", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "papers",
        sa.Column("multimodalFailed", sa.Boolean(), nullable=False, server_default="false"),
    )

    # trace_id（Per Review Fix #8）
    op.add_column(
        "papers",
        sa.Column("traceId", sa.String(36), nullable=True),
    )

    # 创建索引
    op.create_index("idx_papers_trace_id", "papers", ["traceId"])
    op.create_index("idx_papers_search_ready", "papers", ["isSearchReady"])
    op.create_index("idx_papers_notes_ready", "papers", ["isNotesReady"])


def downgrade() -> None:
    """Remove sub-status fields from papers table."""
    # 删除索引
    op.drop_index("idx_papers_notes_ready", table_name="papers")
    op.drop_index("idx_papers_search_ready", table_name="papers")
    op.drop_index("idx_papers_trace_id", table_name="papers")

    # 删除列（逆序）
    op.drop_column("papers", "traceId")
    op.drop_column("papers", "multimodalFailed")
    op.drop_column("papers", "notesFailed")
    op.drop_column("papers", "isNotesReady")
    op.drop_column("papers", "isMultimodalReady")
    op.drop_column("papers", "isSearchReady")