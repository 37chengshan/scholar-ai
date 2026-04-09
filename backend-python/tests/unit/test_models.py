"""Unit tests for SQLAlchemy ORM models.

Tests basic model creation, relationships, and constraints.
"""

import pytest
from datetime import datetime, timezone
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
            email_verified=False,  # Set explicitly since server default
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

    def test_user_timestamps_auto_set(self):
        """Test User timestamps are auto-set on creation."""
        user = User(
            id=str(uuid.uuid4()),
            email="timestamps@example.com",
            name="Timestamp User",
            password_hash="hashed",
        )
        # Server default will set timestamps when persisted
        # Here we just verify the columns exist
        assert hasattr(user, 'created_at')
        assert hasattr(user, 'updated_at')

    def test_user_roles_relationship_type(self):
        """Test User.roles relationship returns UserRole list."""
        from sqlalchemy import inspect
        mapper = inspect(User)
        roles_rel = mapper.relationships.roles
        assert roles_rel.uselist is True  # It's a list relationship


class TestPaperModel:
    """Tests for Paper model."""

    def test_paper_creation(self):
        """Test Paper model can be instantiated."""
        paper = Paper(
            id=str(uuid.uuid4()),
            title="Test Paper",
            user_id="user-123",
            status="pending",  # Set explicitly since server default
            starred=False,  # Set explicitly since server default
            authors=[],  # Set explicitly since server default
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

    def test_paper_user_title_unique_constraint(self):
        """Test Paper has unique constraint on (user_id, title)."""
        from sqlalchemy import inspect
        mapper = inspect(Paper)
        table = mapper.local_table
        constraint_names = [c.name for c in table.constraints]
        assert "unique_user_title" in constraint_names


class TestProcessingTaskModel:
    """Tests for ProcessingTask model."""

    def test_processing_task_creation(self):
        """Test ProcessingTask model can be instantiated."""
        task = ProcessingTask(
            id=str(uuid.uuid4()),
            paper_id="paper-123",
            storage_key="uploads/test.pdf",
            status="pending",  # Set explicitly since server default
            attempts=0,  # Set explicitly since server default
        )
        assert task.status == "pending"
        assert task.attempts == 0
        assert task.storage_key == "uploads/test.pdf"

    def test_task_status_transitions(self):
        """Test ProcessingTask status can transition through states."""
        task = ProcessingTask(
            id=str(uuid.uuid4()),
            paper_id="paper-456",
            storage_key="uploads/test.pdf",
            status="pending",
        )

        # Initial state
        assert task.status == "pending"

        # Transition to processing
        task.status = "processing"
        assert task.status == "processing"

        # Transition to completed
        task.status = "completed"
        task.completed_at = datetime.now(timezone.utc)
        assert task.status == "completed"
        assert task.completed_at is not None

        # Alternative: transition to failed
        task2 = ProcessingTask(
            id=str(uuid.uuid4()),
            paper_id="paper-789",
            storage_key="uploads/test2.pdf",
        )
        task2.status = "failed"
        task2.error_message = "PDF parsing failed"
        assert task2.status == "failed"
        assert task2.error_message == "PDF parsing failed"

    def test_task_retry_attempts_increment(self):
        """Test ProcessingTask attempts increment on retry."""
        task = ProcessingTask(
            id=str(uuid.uuid4()),
            paper_id="paper-123",
            storage_key="uploads/test.pdf",
            attempts=0,
        )

        # Simulate retry
        task.attempts += 1
        task.status = "pending"  # Reset for retry
        assert task.attempts == 1

        # Another retry
        task.attempts += 1
        assert task.attempts == 2

    def test_task_paper_relationship(self):
        """Test ProcessingTask.paper relationship setup."""
        from sqlalchemy import inspect
        mapper = inspect(ProcessingTask)
        rel_names = [rel.key for rel in mapper.relationships]
        assert "paper" in rel_names

    def test_task_indexes(self):
        """Test ProcessingTask has expected indexes."""
        from sqlalchemy import inspect
        mapper = inspect(ProcessingTask)
        table = mapper.local_table
        index_names = [idx.name for idx in table.indexes]
        assert "idx_processing_tasks_paper_id" in index_names
        assert "idx_processing_tasks_status" in index_names

    def test_task_repr(self):
        """Test ProcessingTask __repr__ method."""
        task = ProcessingTask(
            id="task-123",
            paper_id="paper-456",
            storage_key="test.pdf",
            status="pending",
        )
        repr_str = repr(task)
        assert "task-123" in repr_str
        assert "paper-456" in repr_str
        assert "pending" in repr_str


class TestQueryModel:
    """Tests for Query model."""

    def test_query_creation(self):
        """Test Query model can be instantiated."""
        query = Query(
            id=str(uuid.uuid4()),
            question="What is the main finding?",
            user_id="user-123",
            status="pending",  # Set explicitly since server default
            query_type="single",  # Set explicitly since server default
            paper_ids=[],  # Set explicitly since server default
        )
        assert query.question == "What is the main finding?"
        assert query.status == "pending"
        assert query.query_type == "single"
        assert query.paper_ids == []

    def test_query_with_answer(self):
        """Test Query with answer and sources."""
        sources = {
            "chunks": [
                {"chunk_id": "c1", "content": "Source content 1", "score": 0.95},
                {"chunk_id": "c2", "content": "Source content 2", "score": 0.87},
            ]
        }
        query = Query(
            id=str(uuid.uuid4()),
            question="What methodology was used?",
            answer="The study used a mixed-methods approach combining quantitative surveys with qualitative interviews.",
            sources=sources,
            status="completed",
            duration_ms=1523,
            user_id="user-123",
            paper_ids=["paper-1", "paper-2"],
        )
        assert query.answer is not None
        assert query.sources is not None
        assert len(query.sources["chunks"]) == 2
        assert query.duration_ms == 1523
        assert len(query.paper_ids) == 2

    def test_query_status_transitions(self):
        """Test Query status can transition through states."""
        query = Query(
            id=str(uuid.uuid4()),
            question="Test question?",
            user_id="user-123",
            status="pending",
        )

        # Initial state
        assert query.status == "pending"

        # Processing
        query.status = "processing"
        assert query.status == "processing"

        # Completed
        query.status = "completed"
        query.answer = "The answer"
        assert query.status == "completed"
        assert query.answer == "The answer"

    def test_query_user_relationship(self):
        """Test Query.user relationship setup."""
        from sqlalchemy import inspect
        mapper = inspect(Query)
        rel_names = [rel.key for rel in mapper.relationships]
        assert "user" in rel_names

    def test_query_indexes(self):
        """Test Query has expected indexes."""
        from sqlalchemy import inspect
        mapper = inspect(Query)
        table = mapper.local_table
        index_names = [idx.name for idx in table.indexes]
        assert "idx_queries_created_at" in index_names
        assert "idx_queries_user_id" in index_names

    def test_query_repr(self):
        """Test Query __repr__ method."""
        query = Query(
            id="query-123",
            question="This is a very long question that should be truncated in the repr output",
            user_id="user-456",
        )
        repr_str = repr(query)
        assert "query-123" in repr_str
        assert "..." in repr_str


class TestNoteModel:
    """Tests for Note model."""

    def test_note_creation(self):
        """Test Note model can be instantiated."""
        note = Note(
            id=str(uuid.uuid4()),
            user_id="user-123",
            title="My Notes",
            content="# Summary\n\nThis is a summary.",
            tags=[],  # Set explicitly since server default
            paper_ids=[],  # Set explicitly since server default
        )
        assert note.title == "My Notes"
        assert "Summary" in note.content
        assert note.tags == []
        assert note.paper_ids == []

    def test_note_with_papers(self):
        """Test Note with paper references."""
        note = Note(
            id=str(uuid.uuid4()),
            user_id="user-123",
            title="Cross-paper Analysis",
            content="Notes comparing multiple papers...",
            tags=["analysis", "comparison"],
            paper_ids=["paper-1", "paper-2", "paper-3"],
        )
        assert len(note.paper_ids) == 3
        assert "paper-1" in note.paper_ids
        assert len(note.tags) == 2
        assert "analysis" in note.tags

    def test_note_tags_default_empty_list(self):
        """Test Note.tags can be set to empty list."""
        note = Note(
            id=str(uuid.uuid4()),
            user_id="user-123",
            title="Untagged Note",
            content="Content",
            tags=[],
        )
        assert note.tags == []

    def test_note_paper_ids_default_empty_list(self):
        """Test Note.paper_ids can be set to empty list."""
        note = Note(
            id=str(uuid.uuid4()),
            user_id="user-123",
            title="Standalone Note",
            content="Content",
            paper_ids=[],
        )
        assert note.paper_ids == []

    def test_note_user_relationship(self):
        """Test Note.user relationship setup."""
        from sqlalchemy import inspect
        mapper = inspect(Note)
        rel_names = [rel.key for rel in mapper.relationships]
        assert "user" in rel_names

    def test_note_indexes(self):
        """Test Note has expected indexes."""
        from sqlalchemy import inspect
        mapper = inspect(Note)
        table = mapper.local_table
        index_names = [idx.name for idx in table.indexes]
        assert "idx_notes_user_id" in index_names
        assert "idx_notes_created_at" in index_names

    def test_note_repr(self):
        """Test Note __repr__ method."""
        note = Note(
            id="note-123",
            user_id="user-456",
            title="This is a very long title that should be truncated",
            content="Content",
        )
        repr_str = repr(note)
        assert "note-123" in repr_str
        assert "..." in repr_str


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
            color="#FFEB3B",  # Set explicitly since server default
        )
        assert annotation.type == "highlight"
        assert annotation.page_number == 1
        assert annotation.color == "#FFEB3B"

    def test_annotation_types(self):
        """Test Annotation can have different types."""
        types = ["highlight", "underline", "note", "bookmark"]
        for ann_type in types:
            annotation = Annotation(
                id=str(uuid.uuid4()),
                paper_id="paper-123",
                user_id="user-456",
                type=ann_type,
                page_number=1,
                position={},
            )
            assert annotation.type == ann_type


class TestProjectModel:
    """Tests for Project model."""

    def test_project_creation(self):
        """Test Project model can be instantiated."""
        project = Project(
            id=str(uuid.uuid4()),
            user_id="user-123",
            name="Research Project",
            color="#3B82F6",  # Set explicitly since server default
        )
        assert project.name == "Research Project"
        assert project.color == "#3B82F6"

    def test_project_with_color(self):
        """Test Project with custom color."""
        project = Project(
            id=str(uuid.uuid4()),
            user_id="user-123",
            name="ML Research",
            color="#10B981",
        )
        assert project.color == "#10B981"


class TestSessionModel:
    """Tests for Session model."""

    def test_session_creation(self):
        """Test Session model can be instantiated."""
        session = Session(
            id=str(uuid.uuid4()),
            user_id="user-123",
            expires_at=datetime.now(timezone.utc),
            status="active",  # Set explicitly since server default
            message_count=0,  # Set explicitly since server default
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

    def test_paper_no_queries_relationship(self):
        """Test Paper does not have queries relationship (removed due to ARRAY FK)."""
        from sqlalchemy import inspect
        mapper = inspect(Paper)
        rel_names = [rel.key for rel in mapper.relationships]
        assert "queries" not in rel_names


class TestModelConstraints:
    """Tests for model constraints."""

    def test_user_email_unique_constraint(self):
        """Test User has unique constraint on email."""
        from sqlalchemy import inspect
        mapper = inspect(User)
        # Check that email column has unique=True
        email_col = mapper.columns.email
        assert email_col.unique is True