"""add knowledge_bases table

Revision ID: 001_add_knowledge_bases
Revises:
Create Date: 2026-04-11

This migration creates the knowledge_bases table for KnowledgeBase model.
Per D-07, D-09: KB专用API，KB全局配置字段继承给论文。

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "001_add_knowledge_bases"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create knowledge_bases table."""
    op.create_table(
        "knowledge_bases",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("description", sa.String(200), nullable=True),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("paper_count", sa.Integer(), nullable=True, default=0),
        sa.Column("chunk_count", sa.Integer(), nullable=True, default=0),
        sa.Column("entity_count", sa.Integer(), nullable=True, default=0),
        sa.Column("embedding_model", sa.String(), nullable=True, default="bge-m3"),
        sa.Column("parse_engine", sa.String(), nullable=True, default="docling"),
        sa.Column("chunk_strategy", sa.String(), nullable=True, default="by-paragraph"),
        sa.Column("enable_graph", sa.Boolean(), nullable=True, default=False),
        sa.Column("enable_imrad", sa.Boolean(), nullable=True, default=True),
        sa.Column(
            "enable_chart_understanding", sa.Boolean(), nullable=True, default=False
        ),
        sa.Column(
            "enable_multimodal_search", sa.Boolean(), nullable=True, default=False
        ),
        sa.Column("enable_comparison", sa.Boolean(), nullable=True, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes
    op.create_index("idx_knowledge_bases_user_id", "knowledge_bases", ["user_id"])
    op.create_index("idx_knowledge_bases_category", "knowledge_bases", ["category"])

    # Add knowledge_base_id column to papers table
    op.add_column(
        "papers",
        sa.Column(
            "knowledge_base_id",
            sa.String(),
            sa.ForeignKey("knowledge_bases.id"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Drop knowledge_bases table."""
    # Remove knowledge_base_id column from papers
    op.drop_column("papers", "knowledge_base_id")

    # Drop indexes
    op.drop_index("idx_knowledge_bases_category", table_name="knowledge_bases")
    op.drop_index("idx_knowledge_bases_user_id", table_name="knowledge_bases")

    # Drop table
    op.drop_table("knowledge_bases")
