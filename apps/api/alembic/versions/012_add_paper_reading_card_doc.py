"""add paper reading card doc

Revision ID: 012_add_paper_reading_card_doc
Revises: 011_add_notes_2_0_fields
Create Date: 2026-04-27
"""

from alembic import op
import sqlalchemy as sa


revision = "012_add_paper_reading_card_doc"
down_revision = "011_add_notes_2_0_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("papers", sa.Column("readingCardDoc", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("papers", "readingCardDoc")
