"""add tasks, system, and remaining tables

Revision ID: 006_add_tasks_and_system
Revises: 006_add_content_papers
Create Date: 2026-04-14

Domain C: Task tracking and system tables.
Uses raw SQL with CREATE TABLE IF NOT EXISTS for idempotency.

Also adds batch_id FK to papers after paper_batches is created.
"""

revision = "006_add_tasks_and_system"
down_revision = "006_add_content_papers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from alembic import op
    from sqlalchemy.dialects.postgresql import JSON, JSONB

    # ─── processing_tasks (FK → papers) ──────────────────────────────────────

    op.execute("""
        CREATE TABLE IF NOT EXISTS processing_tasks (
            id VARCHAR(36) PRIMARY KEY,
            paper_id VARCHAR(36) NOT NULL REFERENCES papers(id) ON DELETE CASCADE UNIQUE,
            status VARCHAR NOT NULL DEFAULT 'pending',
            storage_key VARCHAR NOT NULL,
            error_message VARCHAR,
            attempts INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            completed_at TIMESTAMP WITH TIME ZONE,
            checkpoint_stage VARCHAR(50),
            checkpoint_storage_key VARCHAR(255),
            checkpoint_version INTEGER NOT NULL DEFAULT 0,
            stage_timings JSON,
            failure_stage VARCHAR(20),
            failure_code VARCHAR(100),
            failure_message TEXT,
            is_retryable BOOLEAN NOT NULL DEFAULT true,
            trace_id VARCHAR(36)
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_processing_tasks_paper_id ON processing_tasks (paper_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_processing_tasks_status ON processing_tasks (status)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_processing_tasks_trace_id ON processing_tasks (trace_id)"
    )

    # ─── notes_generation_tasks (FK → papers) ─────────────────────────────────

    op.execute("""
        CREATE TABLE IF NOT EXISTS notes_generation_tasks (
            id VARCHAR(36) PRIMARY KEY,
            paper_id VARCHAR(36) NOT NULL REFERENCES papers(id) ON DELETE CASCADE UNIQUE,
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            claimed_by VARCHAR(50),
            claimed_at TIMESTAMP WITH TIME ZONE,
            error_message TEXT,
            attempts INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            completed_at TIMESTAMP WITH TIME ZONE
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_notes_tasks_status ON notes_generation_tasks (status)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_notes_tasks_paper_id ON notes_generation_tasks (paper_id)"
    )

    # ─── reading_progress (FK → papers, users) ────────────────────────────────

    op.execute("""
        CREATE TABLE IF NOT EXISTS reading_progress (
            id VARCHAR(36) PRIMARY KEY,
            "paperId" VARCHAR(36) NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
            "userId" VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            current_page INTEGER NOT NULL DEFAULT 1,
            total_pages INTEGER,
            last_read_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
    """)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'unique_paper_user'
            ) THEN
                ALTER TABLE reading_progress ADD CONSTRAINT unique_paper_user UNIQUE ("paperId", "userId");
            END IF;
        END
        $$
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_reading_progress_last_read ON reading_progress (last_read_at)"
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_reading_progress_userId ON reading_progress ("userId")'
    )

    # ─── paper_batches (FK → users) ───────────────────────────────────────────

    op.execute("""
        CREATE TABLE IF NOT EXISTS paper_batches (
            id VARCHAR(36) PRIMARY KEY,
            "userId" VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            total_files INTEGER NOT NULL,
            uploaded_count INTEGER NOT NULL DEFAULT 0,
            status VARCHAR NOT NULL DEFAULT 'uploading',
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
    """)
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_paper_batches_user_id ON paper_batches ("userId")'
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_paper_batches_status ON paper_batches (status)"
    )

    # ─── Add batch_id FK to papers ────────────────────────────────────────────

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'papers' AND column_name = 'batch_id'
            ) THEN
                ALTER TABLE papers ADD COLUMN batch_id VARCHAR(36) REFERENCES paper_batches(id) ON DELETE SET NULL;
            END IF;
        END
        $$
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_papers_batch_id ON papers (batch_id)")

    # ─── upload_history (FK → users, papers) ─────────────────────────────────

    op.execute("""
        CREATE TABLE IF NOT EXISTS upload_history (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            paper_id VARCHAR(36) REFERENCES papers(id) ON DELETE SET NULL,
            filename VARCHAR NOT NULL,
            status VARCHAR NOT NULL DEFAULT 'PROCESSING',
            chunks_count INTEGER,
            llm_tokens INTEGER,
            page_count INTEGER,
            image_count INTEGER,
            table_count INTEGER,
            error_message TEXT,
            processing_time INTEGER,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_upload_history_user_created ON upload_history (user_id, created_at)"
    )

    # ─── chat_messages (FK → sessions) ───────────────────────────────────────

    op.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id VARCHAR(36) PRIMARY KEY,
            session_id VARCHAR(36) NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
            role VARCHAR(20) NOT NULL,
            content TEXT NOT NULL,
            tool_name VARCHAR(100),
            tool_params JSONB,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            reasoning_content TEXT,
            current_phase VARCHAR(50),
            tool_timeline JSONB,
            citations JSONB,
            stream_status VARCHAR(20),
            tokens_used INTEGER,
            cost DOUBLE PRECISION,
            duration_ms INTEGER
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at ON chat_messages (created_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON chat_messages (session_id)"
    )

    # ─── token_usage_logs (FK → users, sessions) ───────────────────────────────

    op.execute("""
        CREATE TABLE IF NOT EXISTS token_usage_logs (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            session_id VARCHAR(36) REFERENCES sessions(id) ON DELETE SET NULL,
            model VARCHAR(50) NOT NULL,
            input_tokens INTEGER NOT NULL,
            output_tokens INTEGER NOT NULL,
            total_tokens INTEGER NOT NULL,
            cost_cny NUMERIC NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_token_usage_session ON token_usage_logs (session_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_token_usage_user_date ON token_usage_logs (user_id, created_at)"
    )

    # ─── user_memories (FK → users) ───────────────────────────────────────────

    op.execute("""
        CREATE TABLE IF NOT EXISTS user_memories (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            content TEXT NOT NULL,
            memory_type VARCHAR NOT NULL,
            "metadata" JSONB,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_user_memories_user_id ON user_memories (user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_user_memories_memory_type ON user_memories (memory_type)"
    )

    # ─── knowledge_maps (FK → users) ──────────────────────────────────────────

    op.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_maps (
            id VARCHAR(36) PRIMARY KEY,
            name VARCHAR NOT NULL,
            description TEXT,
            domain VARCHAR,
            "nodeCount" INTEGER NOT NULL DEFAULT 0,
            "edgeCount" INTEGER NOT NULL DEFAULT 0,
            "createdAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            "updatedAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            "userId" VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # ─── configs (no FK) ───────────────────────────────────────────────────────

    op.execute("""
        CREATE TABLE IF NOT EXISTS configs (
            id VARCHAR(36) PRIMARY KEY,
            "key" VARCHAR NOT NULL UNIQUE,
            value JSON NOT NULL,
            description TEXT,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
    """)
    op.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_configs_key ON configs ("key")')


def downgrade() -> None:
    from alembic import op

    op.execute("DROP TABLE IF EXISTS configs CASCADE")
    op.execute("DROP TABLE IF EXISTS knowledge_maps CASCADE")
    op.execute("DROP TABLE IF EXISTS user_memories CASCADE")
    op.execute("DROP TABLE IF EXISTS token_usage_logs CASCADE")
    op.execute("DROP TABLE IF EXISTS chat_messages CASCADE")
    op.execute("DROP TABLE IF EXISTS upload_history CASCADE")
    op.execute("DROP INDEX IF EXISTS idx_papers_batch_id")
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'papers' AND column_name = 'batch_id'
            ) THEN
                ALTER TABLE papers DROP COLUMN batch_id;
            END IF;
        END
        $$
    """)
    op.execute("DROP TABLE IF EXISTS paper_batches CASCADE")
    op.execute("DROP TABLE IF EXISTS reading_progress CASCADE")
    op.execute("DROP TABLE IF EXISTS notes_generation_tasks CASCADE")
    op.execute("DROP TABLE IF EXISTS processing_tasks CASCADE")
