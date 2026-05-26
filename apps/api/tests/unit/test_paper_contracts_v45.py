from __future__ import annotations

from types import SimpleNamespace
from typing import AsyncIterator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.papers import router
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
