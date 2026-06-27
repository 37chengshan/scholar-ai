"""Add review draft/run tables and align paper metadata indexes.

Revision ID: 015_add_review_tables_and_align_paper_indexes
Revises: 014_add_answer_contract_to_chat_messages
Create Date: 2026-05-26
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "015_add_review_tables_and_align_paper_indexes"
down_revision = "014_add_answer_contract_to_chat_messages"
branch_labels = None
depends_on = None


def _table_names(bind) -> set[str]:
    return set(sa.inspect(bind).get_table_names())


def _index_names(bind, table_name: str) -> set[str]:
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        return set()
    return {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    existing_tables = _table_names(bind)

    if "review_drafts" not in existing_tables:
        op.create_table(
            "review_drafts",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("knowledge_base_id", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column(
                "title",
                sa.String(length=200),
                nullable=False,
                server_default="Review Draft",
            ),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="idle"),
            sa.Column(
                "source_paper_ids",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'[]'::json"),
            ),
            sa.Column("question", sa.String(length=500), nullable=True),
            sa.Column(
                "outline_doc",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'{}'::json"),
            ),
            sa.Column(
                "draft_doc",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'{}'::json"),
            ),
            sa.Column(
                "quality",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'{}'::json"),
            ),
            sa.Column("trace_id", sa.String(length=64), nullable=True),
            sa.Column("run_id", sa.String(length=64), nullable=True),
            sa.Column("error_state", sa.String(length=64), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.ForeignKeyConstraint(["knowledge_base_id"], ["knowledge_bases.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("idx_review_drafts_kb_user", "review_drafts", ["knowledge_base_id", "user_id"])
        op.create_index("idx_review_drafts_status", "review_drafts", ["status"])

    existing_tables = _table_names(bind)
    if "review_runs" not in existing_tables:
        op.create_table(
            "review_runs",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("knowledge_base_id", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column("review_draft_id", sa.String(), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
            sa.Column("scope", sa.String(length=32), nullable=False, server_default="full_kb"),
            sa.Column(
                "input_payload",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'{}'::json"),
            ),
            sa.Column(
                "steps",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'[]'::json"),
            ),
            sa.Column(
                "tool_events",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'[]'::json"),
            ),
            sa.Column(
                "artifacts",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'[]'::json"),
            ),
            sa.Column(
                "evidence",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'[]'::json"),
            ),
            sa.Column(
                "recovery_actions",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'[]'::json"),
            ),
            sa.Column("trace_id", sa.String(length=64), nullable=True),
            sa.Column("error_state", sa.String(length=64), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.ForeignKeyConstraint(["knowledge_base_id"], ["knowledge_bases.id"]),
            sa.ForeignKeyConstraint(["review_draft_id"], ["review_drafts.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("idx_review_runs_kb_user", "review_runs", ["knowledge_base_id", "user_id"])
        op.create_index("idx_review_runs_draft", "review_runs", ["review_draft_id"])
        op.create_index("idx_review_runs_status", "review_runs", ["status"])

    paper_indexes = _index_names(bind, "papers")
    if "idx_papers_userId" in paper_indexes and "idx_papers_user_id" not in paper_indexes:
        op.execute('ALTER INDEX "idx_papers_userId" RENAME TO idx_papers_user_id')


def downgrade() -> None:
    bind = op.get_bind()
    paper_indexes = _index_names(bind, "papers")
    if "idx_papers_user_id" in paper_indexes and "idx_papers_userId" not in paper_indexes:
        op.execute('ALTER INDEX "idx_papers_user_id" RENAME TO "idx_papers_userId"')

    existing_tables = _table_names(bind)
    if "review_runs" in existing_tables:
        op.drop_index("idx_review_runs_status", table_name="review_runs")
        op.drop_index("idx_review_runs_draft", table_name="review_runs")
        op.drop_index("idx_review_runs_kb_user", table_name="review_runs")
        op.drop_table("review_runs")

    existing_tables = _table_names(bind)
    if "review_drafts" in existing_tables:
        op.drop_index("idx_review_drafts_status", table_name="review_drafts")
        op.drop_index("idx_review_drafts_kb_user", table_name="review_drafts")
        op.drop_table("review_drafts")
