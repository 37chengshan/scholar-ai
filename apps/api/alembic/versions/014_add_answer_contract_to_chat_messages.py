"""add answer contract fields to chat_messages

Revision ID: 014_add_answer_contract_to_chat_messages
Revises: 013_add_processing_task_reliability_fields
Create Date: 2026-05-06
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "014_add_answer_contract_to_chat_messages"
down_revision = "013_add_processing_task_reliability_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "chat_messages",
        sa.Column(
            "answer_contract",
            JSONB(),
            nullable=True,
            comment="Structured answer contract payload for session history rehydration",
        ),
    )
    op.add_column(
        "chat_messages",
        sa.Column(
            "response_type",
            sa.String(length=32),
            nullable=True,
            comment="Structured response type for session history rehydration",
        ),
    )
    op.add_column(
        "chat_messages",
        sa.Column(
            "trace_id",
            sa.String(length=64),
            nullable=True,
            comment="Trace identifier for the message payload",
        ),
    )
    op.add_column(
        "chat_messages",
        sa.Column(
            "run_id",
            sa.String(length=64),
            nullable=True,
            comment="Run identifier for the message payload",
        ),
    )


def downgrade() -> None:
    op.drop_column("chat_messages", "run_id")
    op.drop_column("chat_messages", "trace_id")
    op.drop_column("chat_messages", "response_type")
    op.drop_column("chat_messages", "answer_contract")
