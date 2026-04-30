from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.source_adapters.base_adapter import MetadataPreview, SourceResolution
from app.services.source_adapters.s2_adapter import S2Adapter


class _CacheStub:
    def __init__(self, payload: str | None):
        self.payload = payload
        self.last_set: tuple[str, str, int] | None = None

    def make_s2_cache_key(self, paper_id: str) -> str:
        return f"s2:{paper_id}"

    async def get(self, key: str) -> str | None:
        return self.payload

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        self.payload = value
        self.last_set = (key, value, ttl_seconds)


@pytest.mark.asyncio
async def test_fetch_metadata_treats_arxiv_external_id_as_pdf_fallback(mocker):
    adapter = S2Adapter()
    cache = _CacheStub(
        '{"title":"Attention is All you Need","authors":[],"year":2017,"abstract":"","venue":"NIPS",'
        '"pdf_available":false,"pdf_source":null,"citation_count":0,'
        '"external_ids":{"s2":"paper-1","arxiv":"1706.03762"}}'
    )
    mocker.patch("app.services.source_adapters.s2_adapter.get_import_cache", AsyncMock(return_value=cache))

    metadata = await adapter.fetch_metadata(
        SourceResolution(resolved=True, source_type="semantic_scholar", canonical_id="paper-1")
    )

    assert metadata.pdf_available is True
    assert metadata.pdf_source == "arxiv"
    assert metadata.external_ids["arxiv"] == "1706.03762"


@pytest.mark.asyncio
async def test_acquire_pdf_delegates_to_arxiv_when_s2_has_no_open_access_pdf(mocker):
    adapter = S2Adapter()
    resolution = SourceResolution(resolved=True, source_type="semantic_scholar", canonical_id="paper-1")
    adapter.fetch_metadata = AsyncMock(
        return_value=MetadataPreview(
            title="Attention is All you Need",
            pdf_available=True,
            pdf_source="arxiv",
            external_ids={"arxiv": "1706.03762"},
        )
    )
    adapter.arxiv_adapter.resolve = AsyncMock(
        return_value=SourceResolution(
            resolved=True,
            source_type="arxiv",
            canonical_id="1706.03762",
            canonical_pdf_url="https://arxiv.org/pdf/1706.03762.pdf",
            external_ids={"arxiv": "1706.03762"},
        )
    )
    adapter.arxiv_adapter.acquire_pdf = AsyncMock(return_value="uploads/test.pdf")

    storage_key = await adapter.acquire_pdf(resolution, "/tmp", "uploads/test.pdf")

    assert storage_key == "uploads/test.pdf"
    adapter.arxiv_adapter.resolve.assert_awaited_once_with("1706.03762")
    adapter.arxiv_adapter.acquire_pdf.assert_awaited_once()


@pytest.mark.asyncio
async def test_acquire_pdf_uses_cached_open_access_url_without_refetch(mocker, tmp_path: Path):
    adapter = S2Adapter()
    resolution = SourceResolution(resolved=True, source_type="semantic_scholar", canonical_id="paper-1")
    adapter.fetch_metadata = AsyncMock(
        return_value=MetadataPreview(
            title="Attention is All you Need",
            pdf_available=True,
            pdf_source="semantic_scholar",
            external_ids={"s2": "paper-1"},
        )
    )
    cache = _CacheStub(
        '{"title":"Attention is All you Need","authors":[],"year":2017,"abstract":"","venue":"NIPS",'
        '"pdf_available":true,"pdf_source":"semantic_scholar","citation_count":0,'
        '"open_access_pdf_url":"https://example.org/paper.pdf","external_ids":{"s2":"paper-1"}}'
    )
    limiter = MagicMock(acquire=AsyncMock(), record_success=MagicMock(), record_failure=MagicMock())
    adapter.s2_service.get_paper_details = AsyncMock()
    response = MagicMock()
    response.content = b"%PDF-1.4 cached"
    response.raise_for_status = MagicMock()
    http_client = AsyncMock()
    http_client.get = AsyncMock(return_value=response)
    http_context = AsyncMock()
    http_context.__aenter__.return_value = http_client
    http_context.__aexit__.return_value = False

    mocker.patch("app.services.source_adapters.s2_adapter.get_import_cache", AsyncMock(return_value=cache))
    mocker.patch("app.services.source_adapters.s2_adapter.get_s2_import_limiter", return_value=limiter)
    mocker.patch("httpx.AsyncClient", return_value=http_context)

    storage_key = await adapter.acquire_pdf(resolution, str(tmp_path), "downloads/paper.pdf")

    assert storage_key == "downloads/paper.pdf"
    assert (tmp_path / "downloads/paper.pdf").read_bytes() == b"%PDF-1.4 cached"
    adapter.s2_service.get_paper_details.assert_not_called()
    http_client.get.assert_awaited_once_with("https://example.org/paper.pdf")


@pytest.mark.asyncio
async def test_acquire_pdf_fetches_url_and_updates_cache_when_missing(mocker, tmp_path: Path):
    adapter = S2Adapter()
    resolution = SourceResolution(resolved=True, source_type="semantic_scholar", canonical_id="paper-2")
    adapter.fetch_metadata = AsyncMock(
        return_value=MetadataPreview(
            title="Paper Two",
            pdf_available=True,
            pdf_source="semantic_scholar",
            external_ids={"s2": "paper-2"},
        )
    )
    cache = _CacheStub(
        '{"title":"Paper Two","authors":[],"year":2020,"abstract":"","venue":"ACL",'
        '"pdf_available":true,"pdf_source":"semantic_scholar","citation_count":0,'
        '"external_ids":{"s2":"paper-2"}}'
    )
    limiter = MagicMock(acquire=AsyncMock(), record_success=MagicMock(), record_failure=MagicMock())
    adapter.s2_service.get_paper_details = AsyncMock(return_value={"openAccessPdf": {"url": "https://example.org/fresh.pdf"}})
    response = MagicMock()
    response.content = b"%PDF-1.4 fresh"
    response.raise_for_status = MagicMock()
    http_client = AsyncMock()
    http_client.get = AsyncMock(return_value=response)
    http_context = AsyncMock()
    http_context.__aenter__.return_value = http_client
    http_context.__aexit__.return_value = False

    mocker.patch("app.services.source_adapters.s2_adapter.get_import_cache", AsyncMock(return_value=cache))
    mocker.patch("app.services.source_adapters.s2_adapter.get_s2_import_limiter", return_value=limiter)
    mocker.patch("httpx.AsyncClient", return_value=http_context)

    storage_key = await adapter.acquire_pdf(resolution, str(tmp_path), "downloads/fresh.pdf")

    assert storage_key == "downloads/fresh.pdf"
    adapter.s2_service.get_paper_details.assert_awaited_once_with(
        paper_id="paper-2",
        fields="openAccessPdf",
        redis_client=None,
    )
    assert cache.last_set is not None
    assert '"open_access_pdf_url": "https://example.org/fresh.pdf"' in cache.last_set[1]
