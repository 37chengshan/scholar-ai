"""add upload_sessions table

Revision ID: 010_add_upload_sessions_table
Revises: 009_widen_import_fk_columns
Create Date: 2026-04-17

Adds resumable upload session state for local-file imports.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "010_add_upload_sessions_table"
down_revision = "009_widen_import_fk_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "upload_sessions",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("import_job_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("knowledge_base_id", sa.String(length=64), nullable=False),
        sa.Column("filename", sa.Text(), nullable=True),
        sa.Column("mime_type", sa.String(length=128), nullable=True),
        sa.Column("storage_key", sa.Text(), nullable=True),
        sa.Column("file_sha256", sa.String(length=64), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("chunk_size", sa.Integer(), nullable=False),
        sa.Column("total_parts", sa.Integer(), nullable=False),
        sa.Column(
            "uploaded_parts",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("uploaded_bytes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="created"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["import_job_id"], ["import_jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("idx_upload_sessions_import_job", "upload_sessions", ["import_job_id"])
    op.create_index("idx_upload_sessions_user_status", "upload_sessions", ["user_id", "status"])
    op.create_index("idx_upload_sessions_hash_size", "upload_sessions", ["file_sha256", "size_bytes"])


def downgrade() -> None:
    op.drop_index("idx_upload_sessions_hash_size", table_name="upload_sessions")
    op.drop_index("idx_upload_sessions_user_status", table_name="upload_sessions")
    op.drop_index("idx_upload_sessions_import_job", table_name="upload_sessions")
    op.drop_table("upload_sessions")
