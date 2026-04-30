"""Unit tests for tasks API routes."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, AsyncIterator
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.tasks import router
from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.services.task_service import TaskService


class FakeSession:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0
        self.refreshed: list[str] = []

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1

    async def refresh(self, task: Any) -> None:
        self.refreshed.append(task.id)


@pytest.fixture
def current_user() -> User:
    return User(
        id="test-user-123",
        email="test@example.com",
        name="Test User",
        password_hash="hashed_password",
        email_verified=True,
    )


@pytest.fixture
def task_fixtures() -> dict[str, SimpleNamespace]:
    paper = SimpleNamespace(id="paper-456", title="Test Paper", status="processing", updated_at=None)
    other_paper = SimpleNamespace(id="paper-789", title="Other Paper", status="pending", updated_at=None)
    now = datetime.now(timezone.utc)

    return {
        "completed": SimpleNamespace(
            id="task-completed",
            paper_id=paper.id,
            paper=paper,
            task_type="pdf_processing",
            status="completed",
            storage_key="test/path.pdf",
            attempts=1,
            created_at=now,
            updated_at=now,
            completed_at=now,
            error_message=None,
            checkpoint_stage="indexing",
            checkpoint_storage_key=None,
            checkpoint_version=2,
            stage_timings={"parsing": 1200},
            failure_stage=None,
            failure_code=None,
            failure_message=None,
            is_retryable=True,
            trace_id="trace-completed",
            retry_trace_id=None,
            cancelled_at=None,
            cancellation_reason=None,
            cost_breakdown=None,
            cache_stats=None,
            queue_wait_ms=90,
        ),
        "failed": SimpleNamespace(
            id="task-failed",
            paper_id=paper.id,
            paper=paper,
            task_type="pdf_processing",
            status="failed",
            storage_key="test/path.pdf",
            attempts=1,
            created_at=now,
            updated_at=now,
            completed_at=None,
            error_message="boom",
            checkpoint_stage="embedding",
            checkpoint_storage_key="checkpoints/task-failed/embedding.json",
            checkpoint_version=3,
            stage_timings={"embedding": 2300},
            failure_stage="embedding",
            failure_code="model_error",
            failure_message="embedding model unavailable",
            is_retryable=True,
            trace_id="trace-failed",
            retry_trace_id=None,
            cancelled_at=None,
            cancellation_reason=None,
            cost_breakdown={"embedding_usd": 0.02},
            cache_stats={"embedding": {"hit": False}},
            queue_wait_ms=180,
        ),
        "running": SimpleNamespace(
            id="task-running",
            paper_id=paper.id,
            paper=paper,
            task_type="pdf_processing",
            status="processing",
            storage_key="test/path.pdf",
            attempts=0,
            created_at=now,
            updated_at=now,
            completed_at=None,
            error_message=None,
            checkpoint_stage="parsing",
            checkpoint_storage_key=None,
            checkpoint_version=1,
            stage_timings={},
            failure_stage=None,
            failure_code=None,
            failure_message=None,
            is_retryable=True,
            trace_id="trace-running",
            retry_trace_id=None,
            cancelled_at=None,
            cancellation_reason=None,
            cost_breakdown=None,
            cache_stats=None,
            queue_wait_ms=40,
        ),
        "foreign": SimpleNamespace(
            id="task-foreign",
            paper_id=other_paper.id,
            paper=other_paper,
            task_type="pdf_processing",
            status="pending",
            storage_key="other/path.pdf",
            attempts=0,
            created_at=now,
            updated_at=now,
            completed_at=None,
            error_message=None,
            checkpoint_stage=None,
            checkpoint_storage_key=None,
            checkpoint_version=0,
            stage_timings={},
            failure_stage=None,
            failure_code=None,
            failure_message=None,
            is_retryable=True,
            trace_id="trace-foreign",
            retry_trace_id=None,
            cancelled_at=None,
            cancellation_reason=None,
            cost_breakdown=None,
            cache_stats=None,
            queue_wait_ms=None,
        ),
    }


@pytest.fixture
def app_with_tasks() -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/tasks")
    return app


@pytest_asyncio.fixture
async def authenticated_client(
    app_with_tasks: FastAPI,
    current_user: User,
) -> AsyncIterator[tuple[AsyncClient, FakeSession]]:
    db = FakeSession()

    async def override_get_db() -> AsyncIterator[FakeSession]:
        yield db

    async def override_get_current_user() -> User:
        return current_user

    app_with_tasks.dependency_overrides[get_db] = override_get_db
    app_with_tasks.dependency_overrides[get_current_user] = override_get_current_user

    transport = ASGITransport(app=app_with_tasks)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, db

    app_with_tasks.dependency_overrides.clear()


@pytest.fixture
def install_task_service_mocks(monkeypatch: pytest.MonkeyPatch, task_fixtures: dict[str, SimpleNamespace]):
    async def list_tasks(db: FakeSession, user_id: str, paper_id: str | None = None, status: str | None = None):
        tasks = [task_fixtures["completed"], task_fixtures["failed"], task_fixtures["running"]]
        if paper_id:
            tasks = [task for task in tasks if task.paper_id == paper_id]
        if status:
            tasks = [task for task in tasks if task.status == status]
        return tasks

    async def get_task(db: FakeSession, task_id: str, user_id: str):
        for task in task_fixtures.values():
            if task.id == task_id and task.paper.title == "Test Paper":
                return task
        raise ValueError("Task not found")

    async def retry_task(db: FakeSession, task_id: str, user_id: str):
        if task_id == "task-failed":
            task = task_fixtures["failed"]
            retry_trace_id = str(uuid4())
            task.status = "pending"
            task.attempts = 2
            task.error_message = None
            task.failure_message = None
            task.failure_code = None
            task.retry_trace_id = retry_trace_id
            task.trace_id = retry_trace_id
            return task
        if task_id == "task-running":
            raise ValueError("Only failed tasks can be retried")
        if task_id == "task-non-retryable":
            raise PermissionError("Task is not retryable")
        raise ValueError("Task not found")

    async def cancel_task(db: FakeSession, task_id: str, user_id: str):
        if task_id == "task-running":
            task = task_fixtures["running"]
            task.status = "cancelled"
            task.cancelled_at = datetime.now(timezone.utc)
            task.cancellation_reason = "user_request"
            task.failure_stage = "cancelled"
            task.failure_code = "user_cancelled"
            return task
        if task_id == "task-completed":
            raise RuntimeError("Cannot cancel task in status: completed")
        raise ValueError("Task not found")

    monkeypatch.setattr(TaskService, "list_tasks", staticmethod(list_tasks))
    monkeypatch.setattr(TaskService, "get_task", staticmethod(get_task))
    monkeypatch.setattr(TaskService, "retry_task", staticmethod(retry_task))
    monkeypatch.setattr(TaskService, "cancel_task", staticmethod(cancel_task))


@pytest.mark.asyncio
async def test_list_tasks_returns_user_tasks(
    authenticated_client: tuple[AsyncClient, FakeSession],
    install_task_service_mocks,
):
    client, _ = authenticated_client
    response = await client.get("/api/v1/tasks")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["total"] == 3
    assert {task["id"] for task in payload["tasks"]} == {
        "task-completed",
        "task-failed",
        "task-running",
    }
    assert all(task["paper_title"] == "Test Paper" for task in payload["tasks"])
    assert all("task_type" in task for task in payload["tasks"])
    assert any(task["currentStage"] == "completed" for task in payload["tasks"])


@pytest.mark.asyncio
async def test_list_tasks_with_status_filter(
    authenticated_client: tuple[AsyncClient, FakeSession],
    install_task_service_mocks,
):
    client, _ = authenticated_client
    response = await client.get("/api/v1/tasks", params={"status_filter": "failed"})

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["total"] == 1
    assert payload["tasks"][0]["id"] == "task-failed"


@pytest.mark.asyncio
async def test_get_task_returns_enriched_details(
    authenticated_client: tuple[AsyncClient, FakeSession],
    install_task_service_mocks,
):
    client, _ = authenticated_client
    response = await client.get("/api/v1/tasks/task-failed")

    assert response.status_code == 200
    task = response.json()["data"]
    assert task["id"] == "task-failed"
    assert task["failure_code"] == "model_error"
    assert task["failure_stage"] == "embedding"
    assert task["checkpoint_stage"] == "embedding"
    assert task["stage_timings"] == {"embedding": 2300}
    assert task["is_retryable"] is True
    assert task["task_type"] == "pdf_processing"
    assert task["cache_stats"] == {"embedding": {"hit": False}}


@pytest.mark.asyncio
async def test_get_foreign_task_returns_404(
    authenticated_client: tuple[AsyncClient, FakeSession],
    install_task_service_mocks,
):
    client, _ = authenticated_client
    response = await client.get("/api/v1/tasks/task-foreign")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_retry_failed_task_preserves_recovery_metadata(
    authenticated_client: tuple[AsyncClient, FakeSession],
    install_task_service_mocks,
):
    client, db = authenticated_client
    response = await client.post("/api/v1/tasks/task-failed/retry")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "pending"
    assert data["recovery"] == {
        "checkpoint_stage": "embedding",
        "checkpoint_version": 3,
        "retry_trace_id": data["retry_trace_id"],
    }
    assert db.commits == 1
    assert db.refreshed == ["task-failed"]


@pytest.mark.asyncio
async def test_retry_non_retryable_task_returns_409(
    authenticated_client: tuple[AsyncClient, FakeSession],
    install_task_service_mocks,
    monkeypatch: pytest.MonkeyPatch,
):
    client, db = authenticated_client

    async def non_retryable(db_session: FakeSession, task_id: str, user_id: str):
        raise PermissionError("Task is not retryable")

    monkeypatch.setattr(TaskService, "retry_task", staticmethod(non_retryable))
    response = await client.post("/api/v1/tasks/task-failed/retry")

    assert response.status_code == 409
    assert db.rollbacks == 1


@pytest.mark.asyncio
async def test_get_task_progress_with_stages(
    authenticated_client: tuple[AsyncClient, FakeSession],
    install_task_service_mocks,
):
    client, _ = authenticated_client
    response = await client.get("/api/v1/tasks/task-completed/progress")

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data["stages"]) == 4
    assert data["progress"] == 100
    assert data["currentStage"] == "completed"


@pytest.mark.asyncio
async def test_cancel_running_task_marks_cancelled(
    authenticated_client: tuple[AsyncClient, FakeSession],
    install_task_service_mocks,
):
    client, db = authenticated_client
    response = await client.delete("/api/v1/tasks/task-running")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "cancelled"
    assert data["cancellation_requested"] is True
    assert db.commits == 1


@pytest.mark.asyncio
async def test_cancel_terminal_task_returns_409(
    authenticated_client: tuple[AsyncClient, FakeSession],
    install_task_service_mocks,
):
    client, db = authenticated_client
    response = await client.delete("/api/v1/tasks/task-completed")

    assert response.status_code == 409
    assert db.rollbacks == 1


@pytest.mark.asyncio
async def test_cancel_missing_task_returns_404(
    authenticated_client: tuple[AsyncClient, FakeSession],
    install_task_service_mocks,
):
    client, db = authenticated_client
    response = await client.delete(f"/api/v1/tasks/{uuid4()}")

    assert response.status_code == 404
    assert db.rollbacks == 1
