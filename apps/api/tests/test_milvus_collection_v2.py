"""Tests for current Milvus paper_contents_v2 collection behavior."""

import pytest
from unittest.mock import MagicMock, patch
from pymilvus import CollectionSchema, FieldSchema, DataType

from app.core.milvus_service import MilvusService, get_milvus_service
from app.config import settings


@pytest.fixture
def mock_collection():
    """Mock Collection object."""
    mock_coll = MagicMock()
    mock_coll.create_index = MagicMock()
    mock_coll.load = MagicMock()
    mock_coll.drop = MagicMock()
    return mock_coll


class TestCreateCollectionV2:
    """Test create_collection_v2 method per D-09."""

    @patch('app.core.milvus_service.Collection')
    def test_create_collection_v2_creates_paper_contents_v2(self, mock_collection_cls):
        """Test create_collection_v2() creates paper_contents_v2 with active embedding dimension."""
        # Setup
        mock_collection = MagicMock()
        mock_collection.create_index = MagicMock()
        mock_collection.load = MagicMock()
        mock_collection_cls.return_value = mock_collection

        service = MilvusService()
        service._connected = True

        # Execute
        service.create_collection_v2()

        # Verify Collection was called with correct name and schema
        mock_collection_cls.assert_called_once()
        call_args = mock_collection_cls.call_args

        # Verify collection name
        assert call_args[0][0] == settings.MILVUS_COLLECTION_CONTENTS_V2
        assert call_args[0][0] == "paper_contents_v2"

        # Verify schema is CollectionSchema
        schema = call_args[0][1]
        assert isinstance(schema, CollectionSchema)

        # Verify schema matches current expanded contents-v2 contract.
        fields = schema.fields
        assert len(fields) == 16

        # Verify embedding field follows the active runtime dimension.
        embedding_field = next(f for f in fields if f.name == "embedding")
        assert embedding_field.dtype == DataType.FLOAT_VECTOR
        assert embedding_field.params['dim'] == service.embedding_dim == 1024

    @patch('app.core.milvus_service.Collection')
    def test_create_collection_v2_schema_fields(self, mock_collection_cls):
        """Test current schema fields per D-09."""
        # Setup
        mock_collection = MagicMock()
        mock_collection_cls.return_value = mock_collection

        service = MilvusService()
        service._connected = True

        # Execute
        service.create_collection_v2()

        # Extract schema
        call_args = mock_collection_cls.call_args
        schema = call_args[0][1]
        fields = schema.fields

        # Verify all required fields
        field_names = [f.name for f in fields]
        expected_fields = [
            'id', 'paper_id', 'user_id', 'page_num', 'content_type', 'section',
            'quality_score', 'word_count', 'has_equations', 'has_figures',
            'extraction_version', 'content_data', 'raw_data', 'embedding',
            'indexable', 'embedding_status',
        ]
        assert set(field_names) == set(expected_fields)

        # Verify key field types per current schema.
        id_field = next(f for f in fields if f.name == 'id')
        assert id_field.dtype == DataType.INT64
        assert id_field.is_primary
        assert id_field.auto_id

        paper_id_field = next(f for f in fields if f.name == 'paper_id')
        assert paper_id_field.dtype == DataType.VARCHAR
        assert paper_id_field.params['max_length'] == 64

        user_id_field = next(f for f in fields if f.name == 'user_id')
        assert user_id_field.dtype == DataType.VARCHAR
        assert user_id_field.params['max_length'] == 64

        page_num_field = next(f for f in fields if f.name == 'page_num')
        assert page_num_field.dtype == DataType.INT64

        content_type_field = next(f for f in fields if f.name == 'content_type')
        assert content_type_field.dtype == DataType.VARCHAR
        assert content_type_field.params['max_length'] == 32

        content_data_field = next(f for f in fields if f.name == 'content_data')
        assert content_data_field.dtype == DataType.VARCHAR
        assert content_data_field.params['max_length'] == 32000

        raw_data_field = next(f for f in fields if f.name == 'raw_data')
        assert raw_data_field.dtype == DataType.JSON

        indexable_field = next(f for f in fields if f.name == 'indexable')
        assert indexable_field.dtype == DataType.BOOL

        embedding_status_field = next(f for f in fields if f.name == 'embedding_status')
        assert embedding_status_field.dtype == DataType.VARCHAR
        assert embedding_status_field.params['max_length'] == 32

    @patch('app.core.milvus_service.Collection')
    def test_create_collection_v2_creates_ivf_flat_index(self, mock_collection_cls):
        """Test IVF_FLAT index creation per current contract."""
        # Setup
        mock_collection = MagicMock()
        mock_collection.create_index = MagicMock()
        mock_collection.load = MagicMock()
        mock_collection_cls.return_value = mock_collection

        service = MilvusService()
        service._connected = True

        # Execute
        service.create_collection_v2()

        # Verify index creation was called
        mock_collection.create_index.assert_called_once()

        # Extract index parameters
        call_args = mock_collection.create_index.call_args
        field_name = call_args[0][0]
        index_params = call_args[0][1]

        # Verify field name
        assert field_name == "embedding"

        # Verify index parameters per D-09, RESEARCH.md 2.2
        assert index_params['metric_type'] == "COSINE"
        assert index_params['index_type'] == "IVF_FLAT"
        assert index_params['params']['nlist'] == 100

        # Verify load was called
        mock_collection.load.assert_called_once()


class TestDropCollection:
    """Test drop_collection method per D-08."""

    @patch('app.core.milvus_service.Collection')
    @patch('app.core.milvus_service.utility.has_collection')
    def test_drop_collection_succeeds_if_collection_exists(self, mock_has_collection, mock_collection_cls):
        """drop_collection() drops an existing collection."""
        # Setup - collection exists
        mock_collection = MagicMock()
        mock_collection.drop = MagicMock()
        mock_collection_cls.return_value = mock_collection
        mock_has_collection.return_value = True

        service = MilvusService()
        service._connected = True

        # Execute
        with patch.object(service, "connect") as mock_connect:
            service.drop_collection("paper_contents")

        # Verify Collection was instantiated with collection name
        mock_collection_cls.assert_called_once_with("paper_contents", using=service._alias)
        mock_connect.assert_called_once()

        # Verify drop was called
        mock_collection.drop.assert_called_once()

    @patch('app.core.milvus_service.utility.has_collection')
    def test_drop_collection_skips_if_collection_not_exists(self, mock_has_collection):
        """drop_collection() skips if the collection does not exist."""
        # Setup - collection does not exist
        mock_has_collection.return_value = False

        service = MilvusService()
        service._connected = True

        # Execute
        with patch.object(service, "connect") as mock_connect:
            service.drop_collection("nonexistent_collection")

        mock_has_collection.assert_called_once_with("nonexistent_collection", using=service._alias)
        mock_connect.assert_called_once()

    @patch('app.core.milvus_service.utility.has_collection')
    @pytest.mark.skip(reason="structlog logs not captured by pytest caplog fixture - log emission verified in test output")
    def test_drop_collection_logs_warning_if_not_exists(self, mock_has_collection, caplog):
        """drop_collection logs warning if collection does not exist."""
        # Setup
        mock_has_collection.return_value = False

        service = MilvusService()
        service._connected = True

        # Execute
        with caplog.at_level("WARNING"):
            service.drop_collection("nonexistent")

        # Verify warning was logged (structlog format)
        # The log output shows: "Collection nonexistent does not exist, skip dropping"
        assert len(caplog.records) > 0
        assert any("does not exist" in str(record) or "does not exist" in getattr(record, 'message', '') for record in caplog.records)


class TestHasCollection:
    """Test has_collection wrapper."""

    @patch('app.core.milvus_service.utility.has_collection')
    def test_has_collection_returns_true_after_creation(self, mock_has_collection):
        """has_collection("paper_contents_v2") returns True after creation."""
        # Setup - simulate collection created
        mock_has_collection.return_value = True

        service = MilvusService()
        service._connected = True

        # Execute
        with patch.object(service, "connect") as mock_connect:
            result = service.has_collection("paper_contents_v2")

        # Verify
        assert result is True
        mock_has_collection.assert_called_once_with("paper_contents_v2", using=service._alias)
        mock_connect.assert_called_once()

    @patch('app.core.milvus_service.utility.has_collection')
    def test_has_collection_returns_false_if_not_exists(self, mock_has_collection):
        """has_collection returns False if collection does not exist."""
        # Setup
        mock_has_collection.return_value = False

        service = MilvusService()
        service._connected = True

        # Execute
        with patch.object(service, "connect") as mock_connect:
            result = service.has_collection("nonexistent")

        # Verify
        assert result is False
        mock_has_collection.assert_called_once_with("nonexistent", using=service._alias)
        mock_connect.assert_called_once()


class TestIntegration:
    """Integration tests for collection lifecycle."""

    @patch('app.core.milvus_service.Collection')
    @patch('app.core.milvus_service.utility.has_collection')
    @patch('app.core.milvus_service.connections.connect')
    def test_create_v2_and_drop_old_collection_workflow(
        self, mock_connect, mock_has_collection, mock_collection_cls
    ):
        """End-to-end workflow: initialize v2, drop old collection."""
        # Setup mocks
        # Create separate mocks for v2 collection, summary collection, and old collection.
        v2_collection = MagicMock()
        v2_collection.create_index = MagicMock()
        v2_collection.load = MagicMock()

        summary_collection = MagicMock()
        summary_collection.create_index = MagicMock()
        summary_collection.load = MagicMock()
        
        old_collection = MagicMock()
        old_collection.drop = MagicMock()
        
        mock_collection_cls.side_effect = [v2_collection, summary_collection, old_collection]
        
        # Collection existence checks
        # First call: checking for paper_contents_v2 (doesn't exist) -> create
        # Second call: checking for paper_contents (exists) -> drop
        # Need to handle the 'using' parameter that gets passed
        def has_collection_side_effect(name, using=None):
            if name == "paper_contents_v2":
                return False  # Doesn't exist, will create
            elif name == "paper_contents":
                return True  # Exists, will drop
            elif name == service.SUMMARY_COLLECTION_NAME:
                return False
            return False
        
        mock_has_collection.side_effect = has_collection_side_effect

        service = MilvusService()

        # Execute workflow via initialize_collections
        service.initialize_collections()

        # Verify v2 collection was created
        assert mock_collection_cls.call_count >= 1
        
        # Verify index created for v2
        v2_collection.create_index.assert_called_once()
        
        # Verify v2 was loaded
        v2_collection.load.assert_called_once()

        # Verify summary collection was created during bootstrap.
        summary_collection.create_index.assert_called_once()
        summary_collection.load.assert_called_once()
        
        # Verify old collection dropped
        old_collection.drop.assert_called_once()


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
