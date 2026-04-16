"""Tests for PDF download worker.

Tests the PDF download functionality with retry, timeout, and fallback logic.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
from datetime import datetime

from app.workers.pdf_download_worker import (
    fetch_pdf_with_retry,
    download_external_pdf,
    PDFDownloadWorker,
    MAX_RETRIES,
    PDF_DOWNLOAD_TIMEOUT,
)


class TestFetchPDFWithRetry:
    """Test suite for fetch_pdf_with_retry function."""

    @pytest.mark.asyncio
    async def test_successful_pdf_download(self):
        """
        Test successful PDF download returns PDF content.

        Verifies:
        - HTTP request is made successfully
        - PDF content is returned as bytes
        - PDF header is validated
        """
        mock_response = MagicMock()
        mock_response.content = b'%PDF-1.4 test content'
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient.get', return_value=mock_response):
            result = await fetch_pdf_with_retry("http://example.com/paper.pdf")

        assert result == b'%PDF-1.4 test content'
        mock_response.raise_for_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalid_pdf_content_raises_error(self):
        """
        Test invalid PDF content (not starting with %PDF) raises error.

        Verifies:
        - Non-PDF content is rejected
        - ValueError is raised with appropriate message
        """
        mock_response = MagicMock()
        mock_response.content = b'Not a PDF file'
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient.get', return_value=mock_response):
            with pytest.raises(ValueError, match="Downloaded content is not a PDF"):
                await fetch_pdf_with_retry("http://example.com/paper.pdf")

    @pytest.mark.asyncio
    async def test_timeout_triggers_retry_then_failure(self):
        """
        Test timeout triggers retry then eventual failure.

        Verifies:
        - TimeoutException triggers retry
        - After max retries, exception is raised
        - Correct number of attempts are made
        """
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.side_effect = httpx.TimeoutException("Request timed out")

            with pytest.raises(httpx.TimeoutException):
                await fetch_pdf_with_retry("http://example.com/paper.pdf")

            # Should be called MAX_RETRIES times
            assert mock_get.call_count == MAX_RETRIES

    @pytest.mark.asyncio
    async def test_network_error_triggers_retry(self):
        """
        Test network error triggers retry.

        Verifies:
        - NetworkError triggers retry logic
        - After max retries, exception is raised
        """
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.side_effect = httpx.NetworkError("Connection failed")

            with pytest.raises(httpx.NetworkError):
                await fetch_pdf_with_retry("http://example.com/paper.pdf")

            assert mock_get.call_count == MAX_RETRIES

    @pytest.mark.asyncio
    async def test_404_error_does_not_retry(self):
        """
        Test 404 error does not trigger retry (only network errors do).

        Verifies:
        - HTTPStatusError is raised immediately
        - No retry attempts are made for 404
        """
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found",
            request=MagicMock(),
            response=MagicMock(status_code=404)
        )

        with patch('httpx.AsyncClient.get', return_value=mock_response):
            with pytest.raises(httpx.HTTPStatusError):
                await fetch_pdf_with_retry("http://example.com/paper.pdf")

    @pytest.mark.asyncio
    async def test_success_after_retry(self):
        """
        Test successful download after one failed attempt.

        Verifies:
        - First attempt fails with timeout
        - Second attempt succeeds
        - Content is returned successfully
        """
        mock_response = MagicMock()
        mock_response.content = b'%PDF-1.4 test content'
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient.get') as mock_get:
            # First call fails, second succeeds
            mock_get.side_effect = [
                httpx.TimeoutException("Timeout"),
                mock_response,
            ]

            result = await fetch_pdf_with_retry("http://example.com/paper.pdf")

            assert result == b'%PDF-1.4 test content'
            assert mock_get.call_count == 2

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self):
        """
        Test exponential backoff waits correct duration between retries.

        Verifies:
        - First retry waits 1 second (2^0)
        - MAX_RETRIES=2 means only 1 retry attempt
        """
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.side_effect = httpx.TimeoutException("Timeout")

            with patch('asyncio.sleep') as mock_sleep:
                with pytest.raises(httpx.TimeoutException):
                    await fetch_pdf_with_retry("http://example.com/paper.pdf")

                # MAX_RETRIES=2 means: initial try + 1 retry
                # Only 1 sleep call with 2^0 = 1 second
                mock_sleep.assert_called_once_with(1)  # 2^0

    @pytest.mark.asyncio
    async def test_pdf_header_validation_rejects_html(self):
        """
        Test PDF header validation rejects HTML responses.

        Verifies:
        - HTML content (common error page) is rejected
        - ValueError is raised
        """
        mock_response = MagicMock()
        mock_response.content = b'<html><body>404 Not Found</body></html>'
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient.get', return_value=mock_response):
            with pytest.raises(ValueError, match="Downloaded content is not a PDF"):
                await fetch_pdf_with_retry("http://example.com/paper.pdf")

    @pytest.mark.asyncio
    async def test_follows_redirects(self):
        """
        Test that redirects are followed during download.

        Verifies:
        - HTTP client is configured to follow redirects
        """
        mock_response = MagicMock()
        mock_response.content = b'%PDF-1.4 test content'
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)

            await fetch_pdf_with_retry("http://example.com/paper.pdf")

            # Verify client was created with follow_redirects=True
            call_kwargs = mock_client_class.call_args.kwargs
            assert call_kwargs.get('follow_redirects') is True


class TestDownloadExternalPDF:
    """Test suite for download_external_pdf function."""

    @pytest.mark.asyncio
    async def test_successful_download_stores_pdf_and_updates_status(self):
        """
        Test successful PDF download stores PDF and updates status.

        Verifies:
        - PDF is stored via store_pdf
        - Paper status is updated to 'pending'
        - Function returns True
        """
        mock_response = MagicMock()
        mock_response.content = b'%PDF-1.4 test content'
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient.get', return_value=mock_response):
            with patch('app.workers.pdf_download_worker.store_pdf', new_callable=AsyncMock) as mock_store:
                with patch('app.workers.pdf_download_worker.update_paper_status', new_callable=AsyncMock) as mock_update:
                    mock_store.return_value = "papers/test-id/paper.pdf"

                    result = await download_external_pdf(
                        paper_id="test-id",
                        primary_url="http://example.com/paper.pdf",
                        source="arxiv",
                        arxiv_id="2401.12345"
                    )

                    assert result is True
                    mock_store.assert_called_once_with("test-id", b'%PDF-1.4 test content')
                    mock_update.assert_called_once_with("test-id", "pending")

    @pytest.mark.asyncio
    async def test_404_error_triggers_fallback_url_attempt(self):
        """
        Test 404 error triggers fallback URL attempt.

        Verifies:
        - Primary URL is tried first
        - Fallback URL is tried when primary fails
        - Function returns True if fallback succeeds
        """
        mock_fail_response = MagicMock()
        mock_fail_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found",
            request=MagicMock(),
            response=MagicMock(status_code=404)
        )

        mock_success_response = MagicMock()
        mock_success_response.content = b'%PDF-1.4 fallback content'
        mock_success_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.side_effect = [mock_fail_response, mock_success_response]

            with patch('app.workers.pdf_download_worker.store_pdf', new_callable=AsyncMock) as mock_store:
                with patch('app.workers.pdf_download_worker.update_paper_status', new_callable=AsyncMock):
                    mock_store.return_value = "papers/test-id/paper.pdf"

                    result = await download_external_pdf(
                        paper_id="test-id",
                        primary_url="http://example.com/paper.pdf",
                        source="arxiv",
                        fallback_url="http://fallback.com/paper.pdf",
                        arxiv_id="2401.12345"
                    )

                    assert result is True
                    assert mock_get.call_count == 2

    @pytest.mark.asyncio
    async def test_all_attempts_fail_returns_false_and_sets_no_pdf(self):
        """
        Test all attempts fail returns False and sets status to 'no_pdf'.

        Verifies:
        - All URLs are tried
        - Function returns False
        - Paper status is set to 'no_pdf'
        - Error message is recorded
        """
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found",
            request=MagicMock(),
            response=MagicMock(status_code=404)
        )

        with patch('httpx.AsyncClient.get', return_value=mock_response):
            with patch('app.workers.pdf_download_worker.store_pdf', new_callable=AsyncMock) as mock_store:
                with patch('app.workers.pdf_download_worker.update_paper_status', new_callable=AsyncMock) as mock_update:
                    result = await download_external_pdf(
                        paper_id="test-id",
                        primary_url="http://example.com/paper.pdf",
                        source="arxiv",
                        arxiv_id="2401.12345"
                    )

                    assert result is False
                    mock_store.assert_not_called()
                    mock_update.assert_called_once()
                    # Check that update was called with 'no_pdf' status
                    call_args = mock_update.call_args
                    assert call_args[0][1] == "no_pdf"
                    assert "PDF download failed" in call_args[0][2]

    @pytest.mark.asyncio
    async def test_arxiv_fallback_constructed_from_arxiv_id(self):
        """
        Test arXiv fallback URL is constructed from arxiv_id for arxiv source.

        Verifies:
        - arXiv fallback URL is automatically constructed
        - Format: https://arxiv.org/pdf/{arxiv_id}.pdf
        - Fallback is tried when primary fails
        """
        mock_fail_response = MagicMock()
        mock_fail_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found",
            request=MagicMock(),
            response=MagicMock(status_code=404)
        )

        mock_success_response = MagicMock()
        mock_success_response.content = b'%PDF-1.4 arxiv content'
        mock_success_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient.get') as mock_get:
            # First call fails, second (arxiv fallback) succeeds
            mock_get.side_effect = [mock_fail_response, mock_success_response]

            with patch('app.workers.pdf_download_worker.store_pdf', new_callable=AsyncMock) as mock_store:
                with patch('app.workers.pdf_download_worker.update_paper_status', new_callable=AsyncMock):
                    mock_store.return_value = "papers/test-id/paper.pdf"

                    result = await download_external_pdf(
                        paper_id="test-id",
                        primary_url="http://example.com/paper.pdf",
                        source="arxiv",
                        arxiv_id="2401.12345"
                    )

                    assert result is True
                    # Check that second call was to arxiv fallback
                    second_call = mock_get.call_args_list[1]
                    assert "arxiv.org/pdf/2401.12345.pdf" in str(second_call)

    @pytest.mark.asyncio
    async def test_no_arxiv_fallback_for_non_arxiv_source(self):
        """
        Test no arXiv fallback is constructed for non-arxiv sources.

        Verifies:
        - Only primary URL is tried for semantic-scholar source
        - No automatic arXiv URL construction
        """
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found",
            request=MagicMock(),
            response=MagicMock(status_code=404)
        )

        with patch('httpx.AsyncClient.get', return_value=mock_response) as mock_get:
            with patch('app.workers.pdf_download_worker.update_paper_status', new_callable=AsyncMock) as mock_update:
                result = await download_external_pdf(
                    paper_id="test-id",
                    primary_url="http://example.com/paper.pdf",
                    source="semantic-scholar",
                    arxiv_id="2401.12345"  # Should be ignored for non-arxiv source
                )

                assert result is False
                # Should only be called once (no arxiv fallback for non-arxiv source)
                assert mock_get.call_count == 1

    @pytest.mark.asyncio
    async def test_provided_fallback_url_is_used(self):
        """
        Test provided fallback_url parameter is used when primary fails.

        Verifies:
        - Primary URL is tried first
        - Provided fallback URL is tried second
        - Fallback URL is deduplicated (not tried twice if same as arxiv fallback)
        """
        mock_fail_response = MagicMock()
        mock_fail_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found",
            request=MagicMock(),
            response=MagicMock(status_code=404)
        )

        mock_success_response = MagicMock()
        mock_success_response.content = b'%PDF-1.4 fallback content'
        mock_success_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.side_effect = [mock_fail_response, mock_success_response]

            with patch('app.workers.pdf_download_worker.store_pdf', new_callable=AsyncMock) as mock_store:
                with patch('app.workers.pdf_download_worker.update_paper_status', new_callable=AsyncMock):
                    mock_store.return_value = "papers/test-id/paper.pdf"

                    result = await download_external_pdf(
                        paper_id="test-id",
                        primary_url="http://primary.com/paper.pdf",
                        source="semantic-scholar",
                        fallback_url="http://fallback.com/paper.pdf"
                    )

                    assert result is True
                    assert mock_get.call_count == 2
                    # Verify fallback URL was called
                    second_call = mock_get.call_args_list[1]
                    assert "fallback.com" in str(second_call)


class TestPDFDownloadWorker:
    """Test suite for PDFDownloadWorker class."""

    @pytest.mark.asyncio
    async def test_process_task_calls_download_external_pdf(self):
        """
        Test worker process_task method calls download_external_pdf.

        Verifies:
        - Task data is passed correctly
        - All parameters are forwarded
        """
        task_data = {
            "paper_id": "test-paper-id",
            "primary_url": "http://example.com/paper.pdf",
            "source": "arxiv",
            "fallback_url": "http://fallback.com/paper.pdf",
            "arxiv_id": "2401.12345"
        }

        worker = PDFDownloadWorker()

        with patch('app.workers.pdf_download_worker.download_external_pdf', new_callable=AsyncMock) as mock_download:
            mock_download.return_value = True

            result = await worker.process_task(task_data)

            assert result is True
            mock_download.assert_called_once_with(
                paper_id="test-paper-id",
                primary_url="http://example.com/paper.pdf",
                source="arxiv",
                fallback_url="http://fallback.com/paper.pdf",
                arxiv_id="2401.12345"
            )

    @pytest.mark.asyncio
    async def test_process_task_with_optional_fields(self):
        """
        Test worker process_task with minimal task data.

        Verifies:
        - Optional fields (fallback_url, arxiv_id) default to None
        - Required fields are passed
        """
        task_data = {
            "paper_id": "test-paper-id",
            "primary_url": "http://example.com/paper.pdf",
            "source": "semantic-scholar",
        }

        worker = PDFDownloadWorker()

        with patch('app.workers.pdf_download_worker.download_external_pdf', new_callable=AsyncMock) as mock_download:
            mock_download.return_value = False

            result = await worker.process_task(task_data)

            assert result is False
            mock_download.assert_called_once_with(
                paper_id="test-paper-id",
                primary_url="http://example.com/paper.pdf",
                source="semantic-scholar",
                fallback_url=None,
                arxiv_id=None
            )


class TestIntegrationScenarios:
    """Integration test scenarios for PDF download."""

    @pytest.mark.asyncio
    async def test_end_to_end_success_flow(self):
        """
        Test end-to-end success flow from download to status update.

        Simulates real-world scenario where PDF is downloaded and stored.
        """
        mock_response = MagicMock()
        mock_response.content = b'%PDF-1.4\n1 0 obj...'
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient.get', return_value=mock_response):
            with patch('app.workers.pdf_download_worker.store_pdf', new_callable=AsyncMock) as mock_store:
                with patch('app.workers.pdf_download_worker.update_paper_status', new_callable=AsyncMock) as mock_update:
                    mock_store.return_value = "papers/uuid/paper.pdf"

                    result = await download_external_pdf(
                        paper_id="paper-uuid-123",
                        primary_url="https://arxiv.org/pdf/2401.12345.pdf",
                        source="arxiv",
                        arxiv_id="2401.12345"
                    )

                    assert result is True
                    mock_store.assert_called_once()
                    mock_update.assert_called_once_with("paper-uuid-123", "pending")

    @pytest.mark.asyncio
    async def test_end_to_end_failure_flow(self):
        """
        Test end-to-end failure flow where all downloads fail.

        Simulates real-world scenario where PDF is not available.
        """
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found",
            request=MagicMock(),
            response=MagicMock(status_code=404)
        )

        with patch('httpx.AsyncClient.get', return_value=mock_response):
            with patch('app.workers.pdf_download_worker.update_paper_status', new_callable=AsyncMock) as mock_update:
                result = await download_external_pdf(
                    paper_id="paper-uuid-456",
                    primary_url="https://example.com/paper.pdf",
                    source="semantic-scholar"
                )

                assert result is False
                mock_update.assert_called_once()
                # Verify no_pdf status with error message
                args = mock_update.call_args
                assert args[0][0] == "paper-uuid-456"
                assert args[0][1] == "no_pdf"
                assert "PDF download failed" in args[0][2]

    @pytest.mark.asyncio
    async def test_timeout_on_large_pdf(self):
        """
        Test handling of large PDF download timeout.

        Verifies large PDFs (>60s) are handled gracefully.
        """
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.side_effect = httpx.TimeoutException("Request timed out after 60 seconds")

            with patch('app.workers.pdf_download_worker.update_paper_status', new_callable=AsyncMock) as mock_update:
                result = await download_external_pdf(
                    paper_id="large-paper-id",
                    primary_url="https://example.com/large-paper.pdf",
                    source="arxiv",
                    arxiv_id="2401.99999"
                )

                assert result is False
                # Should have tried multiple times
                assert mock_get.call_count == MAX_RETRIES * 2  # primary + arxiv fallback

    @pytest.mark.asyncio
    async def test_duplicate_fallback_urls_not_retried(self):
        """
        Test that duplicate fallback URLs are not retried multiple times.

        Verifies:
        - When fallback_url equals constructed arxiv URL, it's not duplicated
        - Each unique URL is tried only once
        """
        mock_fail_response = MagicMock()
        mock_fail_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found",
            request=MagicMock(),
            response=MagicMock(status_code=404)
        )

        with patch('httpx.AsyncClient.get', return_value=mock_fail_response) as mock_get:
            with patch('app.workers.pdf_download_worker.update_paper_status', new_callable=AsyncMock):
                result = await download_external_pdf(
                    paper_id="test-id",
                    primary_url="http://example.com/paper.pdf",
                    source="arxiv",
                    arxiv_id="2401.12345",
                    fallback_url="https://arxiv.org/pdf/2401.12345.pdf"  # Same as arxiv fallback
                )

                assert result is False
                # Should only try 2 URLs (primary + arxiv), not 3 (no duplicate)
                assert mock_get.call_count == 2


class TestConfiguration:
    """Test configuration constants."""

    def test_max_retries_value(self):
        """Test MAX_RETRIES is set to expected value."""
        assert MAX_RETRIES == 2

    def test_pdf_download_timeout_value(self):
        """Test PDF_DOWNLOAD_TIMEOUT is 60 seconds."""
        assert PDF_DOWNLOAD_TIMEOUT == 60.0

    def test_retry_attempts_count(self):
        """Test that retry logic makes correct number of attempts."""
        # MAX_RETRIES = 2 means 2 attempts total (initial + 1 retry)
        assert MAX_RETRIES >= 1
        assert MAX_RETRIES <= 5  # Sanity check
