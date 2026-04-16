"""widen import-system FK columns for UUID compatibility

Revision ID: 009_widen_import_fk_columns
Revises: 008_add_import_batches
Create Date: 2026-04-16

Import tables were initially created with VARCHAR(32) FK columns, but related
entities use UUID-style IDs (36 chars). This migration widens import FK columns
to VARCHAR(64) to prevent StringDataRightTruncationError during ImportJob flow.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "009_widen_import_fk_columns"
down_revision = "008_add_import_batches"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Widen import-system FK columns to 64 chars."""

    # import_jobs foreign-key style columns
    op.alter_column("import_jobs", "user_id", existing_type=sa.String(length=32), type_=sa.String(length=64))
    op.alter_column("import_jobs", "knowledge_base_id", existing_type=sa.String(length=32), type_=sa.String(length=64))
    op.alter_column("import_jobs", "batch_id", existing_type=sa.String(length=32), type_=sa.String(length=64))
    op.alter_column("import_jobs", "dedupe_match_paper_id", existing_type=sa.String(length=32), type_=sa.String(length=64))
    op.alter_column("import_jobs", "paper_id", existing_type=sa.String(length=32), type_=sa.String(length=64))
    op.alter_column("import_jobs", "processing_task_id", existing_type=sa.String(length=32), type_=sa.String(length=64))

    # import_batches foreign-key style columns
    op.alter_column("import_batches", "user_id", existing_type=sa.String(length=32), type_=sa.String(length=64))
    op.alter_column("import_batches", "knowledge_base_id", existing_type=sa.String(length=32), type_=sa.String(length=64))


def downgrade() -> None:
    """Revert import-system FK columns back to 32 chars."""

    # import_batches
    op.alter_column("import_batches", "knowledge_base_id", existing_type=sa.String(length=64), type_=sa.String(length=32))
    op.alter_column("import_batches", "user_id", existing_type=sa.String(length=64), type_=sa.String(length=32))

    # import_jobs
    op.alter_column("import_jobs", "processing_task_id", existing_type=sa.String(length=64), type_=sa.String(length=32))
    op.alter_column("import_jobs", "paper_id", existing_type=sa.String(length=64), type_=sa.String(length=32))
    op.alter_column("import_jobs", "dedupe_match_paper_id", existing_type=sa.String(length=64), type_=sa.String(length=32))
    op.alter_column("import_jobs", "batch_id", existing_type=sa.String(length=64), type_=sa.String(length=32))
    op.alter_column("import_jobs", "knowledge_base_id", existing_type=sa.String(length=64), type_=sa.String(length=32))
    op.alter_column("import_jobs", "user_id", existing_type=sa.String(length=64), type_=sa.String(length=32))
