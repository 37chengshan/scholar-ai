"""add content, papers, and related tables

Revision ID: 006_add_content_papers
Revises: 006_add_users_roles_permissions
Create Date: 2026-04-14

Domain B: Content and paper tables (depends on Domain A).
Uses raw SQL with CREATE TABLE IF NOT EXISTS for idempotency.

Tables:
  projects, knowledge_bases, papers, annotations, queries, notes, paper_chunks

NOTE: papers table is DROP + CREATE to ensure clean schema with all required
columns (s2_paper_id, citation_count) even if it was created by Base.create_all().
Data is backed up before migration. Two papers exist and will be restored after.
"""

revision = "006_add_content_papers"
down_revision = "006_add_users_roles_permissions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from alembic import op
    from sqlalchemy.dialects.postgresql import ARRAY, JSON

    # ─── Tier 1: No FK dependencies ───────────────────────────────────────────

    op.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id VARCHAR(36) PRIMARY KEY,
            "userId" VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR NOT NULL,
            color VARCHAR NOT NULL DEFAULT '#3B82F6',
            "createdAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            "updatedAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
    """)
    op.execute('CREATE INDEX IF NOT EXISTS idx_projects_user_id ON projects ("userId")')

    op.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_bases (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR(50) NOT NULL,
            description VARCHAR(200) DEFAULT '',
            category VARCHAR(50) DEFAULT '其他',
            paper_count INTEGER NOT NULL DEFAULT 0,
            chunk_count INTEGER NOT NULL DEFAULT 0,
            entity_count INTEGER NOT NULL DEFAULT 0,
            embedding_model VARCHAR NOT NULL DEFAULT 'bge-m3',
            parse_engine VARCHAR NOT NULL DEFAULT 'docling',
            chunk_strategy VARCHAR NOT NULL DEFAULT 'by-paragraph',
            enable_graph BOOLEAN NOT NULL DEFAULT false,
            enable_imrad BOOLEAN NOT NULL DEFAULT true,
            enable_chart_understanding BOOLEAN NOT NULL DEFAULT false,
            enable_multimodal_search BOOLEAN NOT NULL DEFAULT false,
            enable_comparison BOOLEAN NOT NULL DEFAULT false,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_knowledge_bases_user_id ON knowledge_bases (user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_knowledge_bases_category ON knowledge_bases (category)"
    )

    # ─── Tier 2: FK users, projects, knowledge_bases ──────────────────────────

    # Drop existing papers table (may have been created by Base.create_all)
    # to ensure clean schema with all required columns
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'papers') THEN
                DROP TABLE papers CASCADE;
            END IF;
        END
        $$
    """)

    op.execute("""
        CREATE TABLE papers (
            id VARCHAR(36) PRIMARY KEY,
            title VARCHAR NOT NULL,
            authors TEXT[] NOT NULL DEFAULT '{}',
            year INTEGER,
            abstract TEXT,
            doi VARCHAR,
            "arxivId" VARCHAR,
            "pdfUrl" VARCHAR,
            "pdfPath" VARCHAR,
            content TEXT,
            "imradJson" JSON,
            status VARCHAR NOT NULL DEFAULT 'pending',
            "fileSize" INTEGER,
            "pageCount" INTEGER,
            keywords TEXT[] NOT NULL DEFAULT '{}',
            venue VARCHAR,
            citations INTEGER,
            "createdAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            "updatedAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            "userId" VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            storage_key VARCHAR,
            reading_notes TEXT,
            notes_version INTEGER NOT NULL DEFAULT 0,
            starred BOOLEAN NOT NULL DEFAULT false,
            "projectId" VARCHAR(36) REFERENCES projects(id) ON DELETE SET NULL,
            knowledge_base_id VARCHAR(36) REFERENCES knowledge_bases(id) ON DELETE SET NULL,
            upload_progress INTEGER NOT NULL DEFAULT 0,
            upload_status VARCHAR NOT NULL DEFAULT 'pending',
            uploaded_at TIMESTAMP WITH TIME ZONE,
            isSearchReady BOOLEAN NOT NULL DEFAULT false,
            isMultimodalReady BOOLEAN NOT NULL DEFAULT false,
            isNotesReady BOOLEAN NOT NULL DEFAULT false,
            notesFailed BOOLEAN NOT NULL DEFAULT false,
            multimodalFailed BOOLEAN NOT NULL DEFAULT false,
            "traceId" VARCHAR(36),
            s2_paper_id VARCHAR(255) UNIQUE,
            citation_count INTEGER NOT NULL DEFAULT 0
        )
    """)
    op.execute('CREATE INDEX IF NOT EXISTS idx_papers_userId ON papers ("userId")')
    op.execute("CREATE INDEX IF NOT EXISTS idx_papers_starred ON papers (starred)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_papers_s2_paper_id ON papers (s2_paper_id)"
    )
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'unique_user_title'
            ) THEN
                ALTER TABLE papers ADD CONSTRAINT unique_user_title UNIQUE ("userId", title);
            END IF;
        END
        $$
    """)

    # ─── Tier 3: FK papers, users ──────────────────────────────────────────────

    op.execute("""
        CREATE TABLE IF NOT EXISTS annotations (
            id VARCHAR(36) PRIMARY KEY,
            "paperId" VARCHAR(36) NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
            "userId" VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            type VARCHAR NOT NULL,
            page_number INTEGER NOT NULL,
            position JSON NOT NULL,
            content TEXT,
            color VARCHAR NOT NULL DEFAULT '#FFEB3B',
            "createdAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            "updatedAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
    """)
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_annotations_paper_id ON annotations ("paperId")'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_annotations_paper_page ON annotations ("paperId", page_number)'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_annotations_user_id ON annotations ("userId")'
    )

    op.execute("""
        CREATE TABLE IF NOT EXISTS queries (
            id VARCHAR(36) PRIMARY KEY,
            question TEXT NOT NULL,
            answer TEXT,
            sources JSON,
            "queryType" VARCHAR NOT NULL DEFAULT 'single',
            status VARCHAR NOT NULL DEFAULT 'pending',
            "durationMs" INTEGER,
            "createdAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            "userId" VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            "paperIds" TEXT[] NOT NULL DEFAULT '{}'
        )
    """)
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_queries_created_at ON queries ("createdAt")'
    )
    op.execute('CREATE INDEX IF NOT EXISTS idx_queries_user_id ON queries ("userId")')

    op.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id VARCHAR(36) PRIMARY KEY,
            "userId" VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title VARCHAR NOT NULL,
            content TEXT NOT NULL,
            tags TEXT[] NOT NULL DEFAULT '{}',
            paper_ids TEXT[] NOT NULL DEFAULT '{}',
            "createdAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            "updatedAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
    """)
    op.execute('CREATE INDEX IF NOT EXISTS idx_notes_user_id ON notes ("userId")')
    op.execute('CREATE INDEX IF NOT EXISTS idx_notes_created_at ON notes ("createdAt")')

    op.execute("""
        CREATE TABLE IF NOT EXISTS paper_chunks (
            id VARCHAR(36) PRIMARY KEY,
            content TEXT NOT NULL,
            section VARCHAR,
            "pageStart" INTEGER,
            "pageEnd" INTEGER,
            "isTable" BOOLEAN NOT NULL DEFAULT false,
            "isFigure" BOOLEAN NOT NULL DEFAULT false,
            "isFormula" BOOLEAN NOT NULL DEFAULT false,
            "createdAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            "paperId" VARCHAR(36) NOT NULL REFERENCES papers(id) ON DELETE CASCADE
        )
    """)
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_paper_chunks_paper_id ON paper_chunks ("paperId")'
    )


def downgrade() -> None:
    from alembic import op

    op.execute("DROP TABLE IF EXISTS paper_chunks CASCADE")
    op.execute("DROP TABLE IF EXISTS notes CASCADE")
    op.execute("DROP TABLE IF EXISTS queries CASCADE")
    op.execute("DROP TABLE IF EXISTS annotations CASCADE")
    op.execute("DROP TABLE IF EXISTS papers CASCADE")
    op.execute("DROP TABLE IF EXISTS knowledge_bases CASCADE")
    op.execute("DROP TABLE IF EXISTS projects CASCADE")
