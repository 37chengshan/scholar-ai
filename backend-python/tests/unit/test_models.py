"""Unit tests for SQLAlchemy ORM models.

Tests basic model creation, relationships, and constraints.
"""

import pytest
from datetime import datetime
import uuid

from app.database import Base, AsyncSessionLocal
from app.models.user import User, Role, UserRole
from app.models.paper import Paper, PaperChunk
from app.models.task import ProcessingTask
from app.models.query import Query
from app.models.orm_note import Note
from app.models.annotation import Annotation
from app.models.project import Project
from app.models.orm_session import Session


class TestUserModel:
    """Tests for User model."""

    def test_user_creation(self):
        """Test User model can be instantiated."""
        user = User(
            id=str(uuid.uuid4()),
            email="test@example.com",
            name="Test User",
            password_hash="hashed_password",
        )
        assert user.email == "test@example.com"
        assert user.name == "Test User"
        assert user.password_hash == "hashed_password"
        assert user.email_verified is False

    def test_user_repr(self):
        """Test User __repr__ method."""
        user = User(
            id="test-id",
            email="test@example.com",
            name="Test User",
            password_hash="hashed",
        )
        assert "test@example.com" in repr(user)


class TestPaperModel:
    """Tests for Paper model."""

    def test_paper_creation(self):
        """Test Paper model can be instantiated."""
        paper = Paper(
            id=str(uuid.uuid4()),
            title="Test Paper",
            user_id="user-123",
        )
        assert paper.title == "Test Paper"
        assert paper.status == "pending"
        assert paper.starred is False
        assert paper.authors == []

    def test_paper_with_metadata(self):
        """Test Paper with additional metadata."""
        paper = Paper(
            id=str(uuid.uuid4()),
            title="Advanced Paper",
            authors=["Author One", "Author Two"],
            year=2024,
            abstract="This is the abstract.",
            user_id="user-123",
            keywords=["AI", "ML"],
        )
        assert len(paper.authors) == 2
        assert paper.year == 2024
        assert len(paper.keywords) == 2


class TestProcessingTaskModel:
    """Tests for ProcessingTask model."""

    def test_processing_task_creation(self):
        """Test ProcessingTask model can be instantiated."""
        task = ProcessingTask(
            id=str(uuid.uuid4()),
            paper_id="paper-123",
            storage_key="uploads/test.pdf",
        )
        assert task.status == "pending"
        assert task.attempts == 0
        assert task.storage_key == "uploads/test.pdf"


class TestQueryModel:
    """Tests for Query model."""

    def test_query_creation(self):
        """Test Query model can be instantiated."""
        query = Query(
            id=str(uuid.uuid4()),
            question="What is the main finding?",
            user_id="user-123",
        )
        assert query.question == "What is the main finding?"
        assert query.status == "pending"
        assert query.query_type == "single"
        assert query.paper_ids == []


class TestNoteModel:
    """Tests for Note model."""

    def test_note_creation(self):
        """Test Note model can be instantiated."""
        note = Note(
            id=str(uuid.uuid4()),
            user_id="user-123",
            title="My Notes",
            content="# Summary\n\nThis is a summary.",
        )
        assert note.title == "My Notes"
        assert "Summary" in note.content
        assert note.tags == []
        assert note.paper_ids == []


class TestAnnotationModel:
    """Tests for Annotation model."""

    def test_annotation_creation(self):
        """Test Annotation model can be instantiated."""
        annotation = Annotation(
            id=str(uuid.uuid4()),
            paper_id="paper-123",
            user_id="user-456",
            type="highlight",
            page_number=1,
            position={"x": 100, "y": 200, "width": 50, "height": 20},
        )
        assert annotation.type == "highlight"
        assert annotation.page_number == 1
        assert annotation.color == "#FFEB3B"


class TestProjectModel:
    """Tests for Project model."""

    def test_project_creation(self):
        """Test Project model can be instantiated."""
        project = Project(
            id=str(uuid.uuid4()),
            user_id="user-123",
            name="Research Project",
        )
        assert project.name == "Research Project"
        assert project.color == "#3B82F6"


class TestSessionModel:
    """Tests for Session model."""

    def test_session_creation(self):
        """Test Session model can be instantiated."""
        session = Session(
            id=str(uuid.uuid4()),
            user_id="user-123",
            expires_at=datetime.utcnow(),
        )
        assert session.status == "active"
        assert session.message_count == 0


class TestModelRelationships:
    """Tests for model relationships."""

    def test_user_paper_relationship(self):
        """Test User-Paper relationship setup."""
        # Just verify the relationship is defined
        from sqlalchemy import inspect
        mapper = inspect(User)
        rel_names = [rel.key for rel in mapper.relationships]
        assert "papers" in rel_names

    def test_paper_chunk_relationship(self):
        """Test Paper-PaperChunk relationship setup."""
        from sqlalchemy import inspect
        mapper = inspect(Paper)
        rel_names = [rel.key for rel in mapper.relationships]
        assert "paper_chunks" in rel_names


class TestModelConstraints:
    """Tests for model constraints."""

    def test_user_email_unique_constraint(self):
        """Test User has unique constraint on email."""
        from sqlalchemy import inspect
        mapper = inspect(User)
        # Check that email column has unique=True
        email_col = mapper.columns.email
        assert email_col.unique is True

    def test_paper_user_title_unique_constraint(self):
        """Test Paper has unique constraint on (user_id, title)."""
        from sqlalchemy import inspect
        mapper = inspect(Paper)
        table = mapper.local_table
        # Check table args for unique constraint
        constraint_names = [c.name for c in table.constraints]
        assert "unique_user_title" in constraint_names