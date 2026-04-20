"""Unit tests for DOI adapter fallback chain (S2 -> Unpaywall -> OpenAlex)."""

import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

os.environ.setdefault("ZHIPU_API_KEY", "test-api-key")
os.environ.setdefault("ENVIRONMENT", "test")

from app.services.source_adapters.doi_adapter import DoiAdapter
from app.services.source_adapters.base_adapter import SourceResolution


@pytest.mark.asyncio
async def test_fetch_metadata_records_tried_sources_and_errors():
    adapter = DoiAdapter()

    resolution = SourceResolution(
        resolved=True,
        source_type="doi",
        canonical_id="10.1000/test-doi",
        external_ids={"doi": "10.1000/test-doi"},
    )

    with patch.object(
        adapter,
        "_discover_pdf_sources",
        AsyncMock(
            return_value=(
                [("openalex", "https://example.com/test.pdf")],
                ["semantic_scholar", "unpaywall", "openalex"],
                {"semantic_scholar": "timeout", "unpaywall": "404"},
            )
        ),
    ), patch.object(adapter.crossref_service, "resolve_doi", AsyncMock(return_value={"title": "T", "authors": [], "year": 2024})):
        metadata = await adapter.fetch_metadata(resolution)

    assert metadata.pdf_available is True
    assert metadata.pdf_source == "openalex"
    assert "doi_tried_sources" in metadata.external_ids
    assert "doi_source_errors" in metadata.external_ids

    tried = json.loads(metadata.external_ids["doi_tried_sources"])
    errors = json.loads(metadata.external_ids["doi_source_errors"])
    assert tried == ["semantic_scholar", "unpaywall", "openalex"]
    assert errors["semantic_scholar"] == "timeout"


@pytest.mark.asyncio
async def test_acquire_pdf_fallbacks_to_next_source(tmp_path: Path):
    adapter = DoiAdapter()

    resolution = SourceResolution(
        resolved=True,
        source_type="doi",
        canonical_id="10.1000/fallback",
    )

    first_error = Exception("first source failed")

    with patch.object(
        adapter,
        "_discover_pdf_sources",
        AsyncMock(
            return_value=(
                [
                    ("semantic_scholar", "https://example.com/first.pdf"),
                    ("unpaywall", "https://example.com/second.pdf"),
                ],
                ["semantic_scholar", "unpaywall", "openalex"],
                {},
            )
        ),
    ):
        with patch("httpx.AsyncClient.get") as mock_get:
            # first source fails, second succeeds
            ok_response = AsyncMock()
            ok_response.raise_for_status.return_value = None
            ok_response.headers = {"content-type": "application/pdf"}
            ok_response.content = b"%PDF-1.4\nhello\n%%EOF"
            mock_get.side_effect = [first_error, ok_response]

            storage_key = await adapter.acquire_pdf(
                resolution,
                str(tmp_path),
                "user/2026/04/20/job.pdf",
            )

    assert storage_key == "user/2026/04/20/job.pdf"
    output_path = tmp_path / storage_key
    assert output_path.exists()
    assert output_path.read_bytes().startswith(b"%PDF-")
