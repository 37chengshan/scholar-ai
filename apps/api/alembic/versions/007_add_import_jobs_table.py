"""add import_jobs table

Revision ID: 007_add_import_jobs
Revises: 006_add_users_roles_permissions
Create Date: 2026-04-14

This migration creates the import_jobs table for ImportJob model.
Per D-01: ImportJob-first pattern - create ImportJob before Paper entity.
Per D-03: Wave 1 only - import_jobs table (import_batches/import_job_events deferred).
Per D-08: State machine with status/stage/progress tracking.

Wave 1 only - batch_id nullable (Wave 3 will add import_batches table).
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "007_add_import_jobs"
down_revision = "006_add_users_roles_permissions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create import_jobs table (Wave 1 only - main table)."""
    op.create_table(
        "import_jobs",
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
        sa.Column(
            "batch_id",
            sa.String(32),
            nullable=True,  # Wave 3 linkage - FK will be added when import_batches table created
        ),
        # Source identification
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("source_ref_raw", sa.Text, nullable=False),
        sa.Column("source_ref_normalized", sa.Text, nullable=True),
        # External source reference
        sa.Column("external_source", sa.String(32), nullable=True),
        sa.Column("external_paper_id", sa.String(128), nullable=True),
        sa.Column("external_version", sa.String(32), nullable=True),
        # State machine
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("stage", sa.String(64), nullable=False),
        sa.Column("progress", sa.Integer, nullable=False, default=0),
        # Deduplication
        sa.Column("dedupe_status", sa.String(32), nullable=False, default="unchecked"),
        sa.Column("dedupe_policy", sa.String(32), nullable=False, default="prompt"),
        sa.Column("dedupe_match_type", sa.String(32), nullable=True),
        sa.Column("dedupe_match_paper_id", sa.String(32), nullable=True),
        sa.Column("dedupe_decision", sa.String(32), nullable=True),
        # Import options
        sa.Column("import_mode", sa.String(32), nullable=False, default="single"),
        sa.Column("auto_attach_to_kb", sa.Boolean, nullable=False, default=True),
        sa.Column(
            "version_policy", sa.String(32), nullable=False, default="latest_if_unspecified"
        ),
        # File info
        sa.Column("filename", sa.Text, nullable=True),
        sa.Column("mime_type", sa.String(128), nullable=True),
        sa.Column("size_bytes", sa.BigInteger, nullable=True),
        sa.Column("storage_key", sa.Text, nullable=True),
        sa.Column("file_sha256", sa.String(64), nullable=True),
        # Resolved metadata (JSONB for flexible data)
        sa.Column("resolved_title", sa.Text, nullable=True),
        sa.Column("resolved_authors", sa.JSON, nullable=True),
        sa.Column("resolved_year", sa.Integer, nullable=True),
        sa.Column("resolved_venue", sa.Text, nullable=True),
        sa.Column("resolved_abstract", sa.Text, nullable=True),
        sa.Column("resolved_pdf_url", sa.Text, nullable=True),
        sa.Column("resolved_metadata", sa.JSON, nullable=True),
        sa.Column("external_ids", sa.JSON, nullable=True),
        # Result linkage
        sa.Column("paper_id", sa.String(32), sa.ForeignKey("papers.id"), nullable=True),
        sa.Column(
            "processing_task_id",
            sa.String(32),
            sa.ForeignKey("processing_tasks.id"),
            nullable=True,
        ),
        # Error handling
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("error_detail", sa.JSON, nullable=True),
        # Retry/idempotency
        sa.Column("retry_count", sa.Integer, nullable=False, default=0),
        sa.Column("idempotency_key", sa.String(128), nullable=True),
        # Frontend guidance - ADDED per plan fix
        sa.Column("next_action", sa.JSON, nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes per gpt意见.md Section 6.3
    op.create_index(
        "idx_import_jobs_user_created_at", "import_jobs", ["user_id", "created_at"]
    )
    op.create_index(
        "idx_import_jobs_kb_status",
        "import_jobs",
        ["knowledge_base_id", "status", "created_at"],
    )
    op.create_index(
        "idx_import_jobs_external_source_paper",
        "import_jobs",
        ["external_source", "external_paper_id"],
    )
    op.create_index("idx_import_jobs_file_sha256", "import_jobs", ["file_sha256"])
    op.create_index("idx_import_jobs_paper_id", "import_jobs", ["paper_id"])
    op.create_index("idx_import_jobs_batch_id", "import_jobs", ["batch_id"])


def downgrade() -> None:
    """Drop import_jobs table."""
    # Drop indexes
    op.drop_index("idx_import_jobs_batch_id", table_name="import_jobs")
    op.drop_index("idx_import_jobs_paper_id", table_name="import_jobs")
    op.drop_index("idx_import_jobs_file_sha256", table_name="import_jobs")
    op.drop_index("idx_import_jobs_external_source_paper", table_name="import_jobs")
    op.drop_index("idx_import_jobs_kb_status", table_name="import_jobs")
    op.drop_index("idx_import_jobs_user_created_at", table_name="import_jobs")

    # Drop table
    op.drop_table("import_jobs")