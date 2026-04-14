"""add users, roles, permissions, and session tables

Revision ID: 006_add_users_roles_permissions
Revises: 005_add_thinking_fields_to_chat_messages
Create Date: 2026-04-14

Domain A: User and permissions tables (foundation layer).
Uses raw SQL with CREATE TABLE IF NOT EXISTS for idempotency.

All other tables depend on users, so this must run first.
"""

revision = "006_add_users_roles_permissions"
down_revision = "005_add_thinking_fields_to_chat_messages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    import sqlalchemy as sa
    from alembic import op
    from sqlalchemy.dialects.postgresql import JSONB

    # ─── Tier 1: No FK dependencies ───────────────────────────────────────────

    op.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id VARCHAR(36) PRIMARY KEY,
            email VARCHAR NOT NULL,
            name VARCHAR NOT NULL,
            password_hash VARCHAR NOT NULL,
            email_verified BOOLEAN NOT NULL DEFAULT false,
            avatar VARCHAR,
            "createdAt" TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
            "updatedAt" TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users (email)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS roles (
            id VARCHAR(36) PRIMARY KEY,
            name VARCHAR NOT NULL,
            description VARCHAR
        )
    """)
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_roles_name ON roles (name)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS permissions (
            id VARCHAR(36) PRIMARY KEY,
            resource VARCHAR NOT NULL,
            action VARCHAR NOT NULL
        )
    """)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'permission_unique'
            ) THEN
                ALTER TABLE permissions ADD CONSTRAINT permission_unique UNIQUE (resource, action);
            END IF;
        END
        $$
    """)

    # ─── Tier 2: FK → users ───────────────────────────────────────────────────

    op.execute("""
        CREATE TABLE IF NOT EXISTS refresh_tokens (
            id VARCHAR(36) PRIMARY KEY,
            "token" VARCHAR NOT NULL,
            "userId" VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            "expiresAt" TIMESTAMP WITH TIME ZONE NOT NULL,
            "createdAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
    """)
    op.execute(
        'CREATE UNIQUE INDEX IF NOT EXISTS idx_refresh_tokens_token ON refresh_tokens ("token")'
    )

    op.execute("""
        CREATE TABLE IF NOT EXISTS user_roles (
            id VARCHAR(36) PRIMARY KEY,
            "userId" VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            "roleId" VARCHAR(36) NOT NULL REFERENCES roles(id) ON DELETE CASCADE
        )
    """)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'user_role_unique'
            ) THEN
                ALTER TABLE user_roles ADD CONSTRAINT user_role_unique UNIQUE ("userId", "roleId");
            END IF;
        END
        $$
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR NOT NULL,
            key_hash VARCHAR NOT NULL,
            prefix VARCHAR,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            last_used_at TIMESTAMP WITH TIME ZONE
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title VARCHAR(255),
            status VARCHAR(50) NOT NULL DEFAULT 'active',
            "metadata" JSONB DEFAULT '{}',
            message_count INTEGER NOT NULL DEFAULT 0,
            tool_call_count INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            last_activity_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            expires_at TIMESTAMP WITH TIME ZONE NOT NULL
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions (expires_at)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions (status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions (user_id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            tool VARCHAR NOT NULL,
            risk_level VARCHAR NOT NULL,
            params JSONB,
            result TEXT,
            tokens_used INTEGER,
            cost_cny DOUBLE PRECISION,
            execution_ms INTEGER,
            ip_address VARCHAR,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs (user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs (created_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_audit_logs_risk_level ON audit_logs (risk_level)"
    )


def downgrade() -> None:
    from alembic import op

    op.execute("DROP TABLE IF EXISTS audit_logs CASCADE")
    op.execute("DROP TABLE IF EXISTS sessions CASCADE")
    op.execute("DROP TABLE IF EXISTS api_keys CASCADE")
    op.execute("DROP TABLE IF EXISTS user_roles CASCADE")
    op.execute("DROP TABLE IF EXISTS refresh_tokens CASCADE")
    op.execute("DROP TABLE IF EXISTS permissions CASCADE")
    op.execute("DROP TABLE IF EXISTS roles CASCADE")
    op.execute("DROP TABLE IF EXISTS users CASCADE")
