"""Tests for Milvus service."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pymilvus.exceptions import MilvusException

from app.core.milvus_service import (
    MilvusService,
    get_milvus_service,
    retry_with_backoff,
    _truncate_varchar,
)


class TestRetryWithBackoff:
    """Test retry decorator."""

    def test_success_no_retry(self):
        """Test function succeeds without retry."""
        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def success_func():
            return "success"

        result = success_func()
        assert result == "success"

    def test_retry_on_failure(self):
        """Test function retries on failure."""
        call_count = 0

        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise MilvusException("Test error")
            return "success"

        result = fail_then_succeed()
        assert result == "success"
        assert call_count == 3

    def test_max_retries_exceeded(self):
        """Test exception raised when max retries exceeded."""
        @retry_with_backoff(max_retries=2, base_delay=0.01)
        def always_fail():
            raise MilvusException("Always fails")

        with pytest.raises(MilvusException):
            always_fail()


class TestMilvusService:
    """Test MilvusService class."""

    def test_init_default(self):
        """Test initialization with default settings."""
        with patch("app.core.milvus_service.settings") as mock_settings:
            mock_settings.MILVUS_HOST = "localhost"
            mock_settings.MILVUS_PORT = 19530

            service = MilvusService()
            assert service.host == "localhost"
            assert service.port == 19530
            assert service.pool_size == 10
            assert service.timeout == 10
            assert service._alias == "scholarai"
            assert not service.is_connected()

    def test_init_custom(self):
        """Test initialization with custom parameters."""
        service = MilvusService(
            host="milvus.example.com",
            port=19531,
            pool_size=20,
            timeout=30
        )
        assert service.host == "milvus.example.com"
        assert service.port == 19531
        assert service.pool_size == 20
        assert service.timeout == 30

    def test_embedding_dim_constants(self):
        """Test embedding dimension constants."""
        # SigLIP for image/table (768-dim)
        assert MilvusService.EMBEDDING_DIM == 768
        # BGE-M3 for text (1024-dim) per D-34
        assert MilvusService.BGE_EMBEDDING_DIM == 1024

    @patch("app.core.milvus_service.connections")
    def test_connect(self, mock_connections):
        """Test connection."""
        service = MilvusService()
        service.connect()

        mock_connections.connect.assert_called_once_with(
            alias="scholarai",
            host="localhost",
            port=19530,
            pool_size=10,
            timeout=10
        )
        assert service.is_connected()

    @patch("app.core.milvus_service.connections")
    def test_connect_already_connected(self, mock_connections):
        """Test connect when already connected."""
        service = MilvusService()
        service.connect()
        mock_connections.connect.assert_called_once()

        # Connect again
        mock_connections.connect.reset_mock()
        service.connect()
        mock_connections.connect.assert_not_called()

    @patch("app.core.milvus_service.connections")
    def test_disconnect(self, mock_connections):
        """Test disconnection."""
        service = MilvusService()
        service.connect()
        service.disconnect()

        mock_connections.disconnect.assert_called_once_with("scholarai")
        assert not service.is_connected()

    @patch("app.core.milvus_service.connections")
    def test_disconnect_not_connected(self, mock_connections):
        """Test disconnect when not connected."""
        service = MilvusService()
        service.disconnect()

        # Should not raise error
        mock_connections.disconnect.assert_not_called()

    def test_singleton(self):
        """Test singleton pattern."""
        service1 = get_milvus_service()
        service2 = get_milvus_service()
        assert service1 is service2


def test_truncate_varchar_leaves_margin_under_schema_limit():
    text = "x" * 9000

    truncated = _truncate_varchar(text, 8000, reserve=128)

    assert len(truncated) == 7872


def test_insert_summaries_batched_truncates_all_string_fields():
    service = MilvusService()
    service._connected = True

    mock_collection = MagicMock()
    mock_result = MagicMock()
    mock_result.primary_keys = [1]
    mock_collection.insert.return_value = mock_result

    with patch.object(service, "has_collection", return_value=True):
        with patch("app.core.milvus_service.Collection", return_value=mock_collection):
            service.insert_summaries_batched(
                [
                    {
                        "paper_id": "p" * 100,
                        "user_id": "u" * 100,
                        "summary_type": "section_summary" * 10,
                        "section_name": "Methods/" * 100,
                        "content_data": "c" * 9000,
                        "embedding": [0.1, 0.2, 0.3],
                    }
                ],
                batch_size=1,
            )

    inserted = mock_collection.insert.call_args.args[0][0]
    assert len(inserted["paper_id"]) <= 60
    assert len(inserted["user_id"]) <= 60
    assert len(inserted["summary_type"]) <= 30
    assert len(inserted["section_name"]) <= 192
    assert len(inserted["content_data"]) <= 7872
