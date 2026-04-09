"""Unit tests for User model.

Tests User model creation, constraints, relationships, and timestamps.
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import MagicMock

from app.models.user import User, Role, UserRole, RefreshToken


class TestUserModel:
    """Tests for User model."""

    def test_user_creation_basic(self):
        """Test User model can be instantiated with basic fields."""
        user = User(
            id=str(uuid4()),
            email="test@example.com",
            name="Test User",
            password_hash="hashed_password_123",
            email_verified=False,  # Set explicitly since server default
        )
        assert user.email == "test@example.com"
        assert user.name == "Test User"
        assert user.password_hash == "hashed_password_123"
        assert user.email_verified is False
        assert user.avatar is None

    def test_user_creation_with_all_fields(self):
        """Test User model with all optional fields."""
        now = datetime.now(timezone.utc)
        user = User(
            id=str(uuid4()),
            email="full@example.com",
            name="Full User",
            password_hash="hashed",
            email_verified=True,
            avatar="https://example.com/avatar.png",
            created_at=now,
            updated_at=now,
        )
        assert user.email_verified is True
        assert user.avatar == "https://example.com/avatar.png"
        assert user.created_at == now
        assert user.updated_at == now

    def test_user_repr(self):
        """Test User __repr__ method."""
        user = User(
            id="user-123",
            email="test@example.com",
            name="Test User",
            password_hash="hashed",
        )
        repr_str = repr(user)
        assert "test@example.com" in repr_str
        assert "user-123" in repr_str

    def test_user_email_unique_constraint(self):
        """Test User has unique constraint on email."""
        from sqlalchemy import inspect
        mapper = inspect(User)
        email_col = mapper.columns.email
        assert email_col.unique is True

    def test_user_email_indexed(self):
        """Test User email column is indexed."""
        from sqlalchemy import inspect
        mapper = inspect(User)
        email_col = mapper.columns.email
        assert email_col.index is True

    def test_user_relationships_defined(self):
        """Test User has all expected relationships."""
        from sqlalchemy import inspect
        mapper = inspect(User)
        rel_names = [rel.key for rel in mapper.relationships]

        expected_relationships = [
            "papers",
            "roles",
            "refresh_tokens",
            "queries",
            "notes",
            "projects",
            "annotations",
            "sessions",
            "upload_history",
            "paper_batches",
            "knowledge_maps",
            "audit_logs",
            "token_usage_logs",
            "reading_progress",
        ]
        for rel in expected_relationships:
            assert rel in rel_names, f"Missing relationship: {rel}"

    def test_user_default_values(self):
        """Test User can have explicit default values."""
        user = User(
            id=str(uuid4()),
            email="defaults@example.com",
            name="Default User",
            password_hash="hashed",
            email_verified=False,  # Explicitly set
        )
        # email_verified can be set explicitly
        assert user.email_verified is False


class TestRoleModel:
    """Tests for Role model."""

    def test_role_creation(self):
        """Test Role model can be instantiated."""
        role = Role(
            id=str(uuid4()),
            name="admin",
            description="Administrator role",
        )
        assert role.name == "admin"
        assert role.description == "Administrator role"

    def test_role_name_unique(self):
        """Test Role name is unique."""
        from sqlalchemy import inspect
        mapper = inspect(Role)
        name_col = mapper.columns.name
        assert name_col.unique is True

    def test_role_repr(self):
        """Test Role __repr__ method."""
        role = Role(id="role-123", name="user")
        assert "user" in repr(role)
        assert "role-123" in repr(role)


class TestUserRoleModel:
    """Tests for UserRole association model."""

    def test_user_role_creation(self):
        """Test UserRole can be instantiated."""
        user_role = UserRole(
            id=str(uuid4()),
            user_id="user-123",
            role_id="role-456",
        )
        assert user_role.user_id == "user-123"
        assert user_role.role_id == "role-456"

    def test_user_role_unique_constraint(self):
        """Test UserRole has unique constraint on (user_id, role_id)."""
        from sqlalchemy import inspect
        mapper = inspect(UserRole)
        table = mapper.local_table
        constraint_names = [c.name for c in table.constraints]
        assert "user_role_unique" in constraint_names


class TestRefreshTokenModel:
    """Tests for RefreshToken model."""

    def test_refresh_token_creation(self):
        """Test RefreshToken can be instantiated."""
        expires = datetime.now(timezone.utc)
        token = RefreshToken(
            id=str(uuid4()),
            token_hash="hashed_token_value",
            user_id="user-123",
            expires_at=expires,
        )
        assert token.token_hash == "hashed_token_value"
        assert token.user_id == "user-123"
        assert token.expires_at == expires

    def test_refresh_token_hash_unique(self):
        """Test RefreshToken token_hash is unique."""
        from sqlalchemy import inspect
        mapper = inspect(RefreshToken)
        token_hash_col = mapper.columns.token_hash
        assert token_hash_col.unique is True

    def test_refresh_token_repr(self):
        """Test RefreshToken __repr__ method."""
        token = RefreshToken(id="token-123", user_id="user-456", expires_at=datetime.now(timezone.utc))
        repr_str = repr(token)
        assert "token-123" in repr_str
        assert "user-456" in repr_str


class TestUserModelIntegration:
    """Integration-style tests for User model relationships."""

    def test_user_papers_relationship_config(self):
        """Test User.papers relationship has cascade delete configured."""
        from sqlalchemy import inspect
        mapper = inspect(User)
        papers_rel = mapper.relationships.papers

        # Verify cascade settings (delete is present)
        assert "delete" in papers_rel.cascade

    def test_user_roles_cascade_delete(self):
        """Test User.roles has cascade delete configured."""
        from sqlalchemy import inspect
        mapper = inspect(User)
        roles_rel = mapper.relationships.roles

        assert "delete" in roles_rel.cascade

    def test_user_refresh_tokens_cascade_delete(self):
        """Test User.refresh_tokens has cascade delete configured."""
        from sqlalchemy import inspect
        mapper = inspect(User)
        rt_rel = mapper.relationships.refresh_tokens

        assert "delete" in rt_rel.cascade