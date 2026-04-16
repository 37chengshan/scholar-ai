"""add import_batches table

Revision ID: 008_add_import_batches
Revises: 007_add_import_jobs
Create Date: 2026-04-14

This migration creates the import_batches table for ImportBatch model.
Per gpt意见.md Section 7.2: Aggregate status for multiple ImportJobs.

Also adds foreign key constraint to import_jobs.batch_id.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "008_add_import_batches"
down_revision = "007_add_import_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create import_batches table and add FK to import_jobs."""
    # Create import_batches table
    op.create_table(
        "import_batches",
        # Primary key
        sa.Column("id", sa.String(32), nullable=False),
        # Foreign keys
        sa.Column(
            "user_id", sa.String(32), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column(
            "knowledge_base_id",
            sa.String(32),
            sa.ForeignKey("knowledge_bases.id"),
            nullable=False,
        ),
        # Status aggregation
        sa.Column("status", sa.String(32), nullable=False, default="created"),
        sa.Column("total_items", sa.Integer, nullable=False),
        sa.Column("completed_items", sa.Integer, nullable=False, default=0),
        sa.Column("failed_items", sa.Integer, nullable=False, default=0),
        sa.Column("cancelled_items", sa.Integer, nullable=False, default=0),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes per gpt意见.md Section 7.2
    op.create_index(
        "idx_import_batches_user_kb", "import_batches", ["user_id", "knowledge_base_id"]
    )
    op.create_index("idx_import_batches_status", "import_batches", ["status"])

    # Add foreign key constraint to import_jobs.batch_id (Wave 3 linkage)
    # Note: batch_id column already exists from Wave 1, now add FK constraint
    op.create_foreign_key(
        "fk_import_jobs_batch_id",
        "import_jobs",
        "import_batches",
        ["batch_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Drop import_batches table and remove FK from import_jobs."""
    # Drop foreign key from import_jobs
    op.drop_constraint("fk_import_jobs_batch_id", "import_jobs", type_="foreignkey")

    # Drop indexes
    op.drop_index("idx_import_batches_status", table_name="import_batches")
    op.drop_index("idx_import_batches_user_kb", table_name="import_batches")

    # Drop table
    op.drop_table("import_batches")