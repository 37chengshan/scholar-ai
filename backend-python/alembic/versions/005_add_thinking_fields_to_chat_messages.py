"""add thinking fields to chat_messages

Revision ID: 005_add_thinking_fields_to_chat_messages
Revises: 004_add_notes_generation_tasks
Create Date: 2026-04-14

This migration adds thinking-related nullable fields to chat_messages table
for future Agent-Native thinking persistence.

Phase 5.2: These fields are RESERVED placeholders. NOT IMPLEMENTED in this phase.
- reasoning_content: Agent reasoning/thinking content
- current_phase: Current processing phase
- tool_timeline: Tool call execution timeline (JSON)
- citations: Source citations for responses (JSON)
- stream_status: Streaming status indicator
- tokens_used: Token consumption
- cost: API cost in USD
- duration_ms: Response duration in milliseconds

NOTE: This phase does NOT implement persistence logic.
All fields are nullable - data is only kept in session memory, not in DB.
Phase 2 will implement actual thinking history across sessions.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

# revision identifiers, used by Alembic.
revision = "005_add_thinking_fields_to_chat_messages"
down_revision = "004_add_notes_generation_tasks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add thinking-related fields to chat_messages table.

    All fields are nullable placeholders for future implementation.
    No data will be written to these fields in Phase 5.2.
    """
    # Agent reasoning/thinking content
    op.add_column(
        "chat_messages",
        sa.Column(
            "reasoning_content",
            sa.Text(),
            nullable=True,
            comment="Phase 5.2 reserved: Agent reasoning content (not implemented)"
        )
    )

    # Current processing phase
    op.add_column(
        "chat_messages",
        sa.Column(
            "current_phase",
            sa.String(50),
            nullable=True,
            comment="Phase 5.2 reserved: Current agent phase (not implemented)"
        )
    )

    # Tool call execution timeline (JSON)
    op.add_column(
        "chat_messages",
        sa.Column(
            "tool_timeline",
            JSON(),
            nullable=True,
            comment="Phase 5.2 reserved: Tool execution timeline (not implemented)"
        )
    )

    # Source citations for agent responses (JSON)
    op.add_column(
        "chat_messages",
        sa.Column(
            "citations",
            JSON(),
            nullable=True,
            comment="Phase 5.2 reserved: Response citations (not implemented)"
        )
    )

    # Streaming status indicator
    op.add_column(
        "chat_messages",
        sa.Column(
            "stream_status",
            sa.String(20),
            nullable=True,
            comment="Phase 5.2 reserved: Stream status (not implemented)"
        )
    )

    # Token consumption for this message
    op.add_column(
        "chat_messages",
        sa.Column(
            "tokens_used",
            sa.Integer(),
            nullable=True,
            comment="Phase 5.2 reserved: Token usage (not implemented)"
        )
    )

    # API cost in USD
    op.add_column(
        "chat_messages",
        sa.Column(
            "cost",
            sa.Float(),
            nullable=True,
            comment="Phase 5.2 reserved: API cost (not implemented)"
        )
    )

    # Response duration in milliseconds
    op.add_column(
        "chat_messages",
        sa.Column(
            "duration_ms",
            sa.Integer(),
            nullable=True,
            comment="Phase 5.2 reserved: Response duration (not implemented)"
        )
    )


def downgrade() -> None:
    """Remove thinking-related fields from chat_messages table."""
    op.drop_column("chat_messages", "duration_ms")
    op.drop_column("chat_messages", "cost")
    op.drop_column("chat_messages", "tokens_used")
    op.drop_column("chat_messages", "stream_status")
    op.drop_column("chat_messages", "citations")
    op.drop_column("chat_messages", "tool_timeline")
    op.drop_column("chat_messages", "current_phase")
    op.drop_column("chat_messages", "reasoning_content")