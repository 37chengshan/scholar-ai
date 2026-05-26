from __future__ import annotations

from types import SimpleNamespace
from typing import AsyncIterator
from unittest.mock import AsyncMock, Mock

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.papers import router
from app.api.papers.paper_status import regenerate_chunks
from app.database import get_db
from app.deps import get_current_user
from app.services.auth_service import User
from app.services.paper_service import PaperService


@pytest.fixture
def current_user() -> User:
    return User(
        id="user-1",
        email="user@example.com",
        name="User One",
        password_hash="hashed",
        email_verified=True,
    )


@pytest.fixture
def papers_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/papers")
    return app


@pytest_asyncio.fixture
async def papers_client(
    papers_app: FastAPI,
    current_user: User,
) -> AsyncIterator[AsyncClient]:
    async def override_get_db() -> AsyncIterator[SimpleNamespace]:
        yield SimpleNamespace()

    async def override_get_current_user() -> User:
        return current_user

    papers_app.dependency_overrides[get_db] = override_get_db
    papers_app.dependency_overrides[get_current_user] = override_get_current_user

    transport = ASGITransport(app=papers_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    papers_app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_post_star_route_returns_enveloped_paper(monkeypatch, papers_client: AsyncClient) -> None:
    async def _fake_toggle_star(db, paper_id: str, user_id: str, starred: bool):
        return SimpleNamespace(
            id=paper_id,
            title="Paper One",
            authors=[],
            year=None,
            abstract=None,
            doi=None,
            arxiv_id=None,
            pdf_url=None,
            pdf_path=None,
            content=None,
            imrad_json=None,
            status="completed",
            file_size=None,
            page_count=None,
            keywords=[],
            venue=None,
            citations=None,
            created_at=None,
            updated_at=None,
            user_id=user_id,
            storage_key=None,
            reading_notes=None,
            reading_card_doc=None,
            notes_version=None,
            starred=starred,
            project_id=None,
            batch_id=None,
            upload_progress=None,
            upload_status=None,
            uploaded_at=None,
            processing_error=None,
            processingStatus=None,
            chunk_count=0,
            is_notes_ready=False,
            notes_failed=False,
            isSearchReady=False,
            searchReadySubstatus=None,
            notesReadySubstatus=None,
        )

    monkeypatch.setattr(PaperService, "toggle_star", staticmethod(_fake_toggle_star))

    response = await papers_client.post("/api/v1/papers/paper-1/star", json={"starred": True})

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["id"] == "paper-1"
    assert payload["data"]["starred"] is True


@pytest.mark.asyncio
async def test_batch_delete_returns_deleted_and_failed_lists(monkeypatch, papers_client: AsyncClient) -> None:
    async def _fake_batch_delete(db, user_id: str, *, paper_ids: list[str]):
        return {
            "deleted_ids": ["paper-1"],
            "failures": [{"id": "paper-2", "reason": "not_found_or_not_owned"}],
        }

    monkeypatch.setattr(PaperService, "batch_delete_for_api", staticmethod(_fake_batch_delete))

    response = await papers_client.post(
        "/api/v1/papers/batch-delete",
        json={"paper_ids": ["paper-1", "paper-2"]},
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["deletedCount"] == 1
    assert payload["deletedIds"] == ["paper-1"]
    assert payload["failedIds"] == ["paper-2"]
    assert payload["failures"] == [{"id": "paper-2", "reason": "not_found_or_not_owned"}]


@pytest.mark.asyncio
async def test_delete_paper_service_cleans_milvus_vectors(monkeypatch) -> None:
    paper = SimpleNamespace(id="paper-1", storage_key="paper.pdf")
    delete_file = AsyncMock()
    milvus = SimpleNamespace(delete_all_vectors_by_paper=Mock())
    db = SimpleNamespace(delete=AsyncMock())

    monkeypatch.setattr(
        "app.services.paper_service.PaperRepository.get_user_paper",
        AsyncMock(return_value=paper),
    )
    monkeypatch.setattr(
        "app.services.paper_service.get_storage_service",
        lambda: SimpleNamespace(delete_file=delete_file),
    )
    monkeypatch.setattr("app.services.paper_service.get_milvus_service", lambda: milvus)

    await PaperService.delete_paper_for_api(db, "user-1", paper_id="paper-1")

    milvus.delete_all_vectors_by_paper.assert_called_once_with("paper-1")
    db.delete.assert_awaited_once_with(paper)


@pytest.mark.asyncio
async def test_regenerate_chunks_cleans_existing_milvus_vectors(monkeypatch, current_user: User) -> None:
    paper = SimpleNamespace(id="paper-1", user_id=current_user.id, storage_key="paper.pdf")
    task = SimpleNamespace(id="task-1", status="failed", error_message="boom", updated_at=None)

    class _Result:
        def __init__(self, value):
            self._value = value

        def scalar_one_or_none(self):
            return self._value

    class _DB:
        def __init__(self):
            self.calls = 0

        async def execute(self, query):
            self.calls += 1
            if self.calls == 1:
                return _Result(paper)
            return _Result(task)

        def add(self, value):
            raise AssertionError("unexpected add")

    milvus = SimpleNamespace(delete_all_vectors_by_paper=Mock())
    monkeypatch.setattr("app.api.papers.paper_status.get_milvus_service", lambda: milvus)

    response = await regenerate_chunks(
        request=SimpleNamespace(url=SimpleNamespace(path="/api/v1/papers/paper-1/regenerate-chunks")),
        paper_id="paper-1",
        current_user=current_user,
        db=_DB(),
    )

    milvus.delete_all_vectors_by_paper.assert_called_once_with("paper-1")
    assert response.data["taskId"] == "task-1"
    assert task.status == "pending"
