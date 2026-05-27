"""Regression tests for MilvusService collection bootstrap behavior."""

from unittest.mock import Mock, patch

from pymilvus.exceptions import MilvusException

import pytest

from app.core.milvus_service import (
    MilvusCollectionSchemaMismatchError,
    MilvusInsertContractError,
    MilvusService,
)
from app.config import settings


def test_get_collection_bootstraps_contents_v2_when_missing():
    """MilvusService should auto-create paper_contents_v2 when it does not exist."""
    service = MilvusService()
    service._connected = True

    with patch.object(service, "has_collection", return_value=False) as mock_has:
        with patch.object(service, "create_collection_v2") as mock_create:
            with patch("app.core.milvus_service.Collection", return_value=Mock()) as mock_collection:
                service.get_collection(settings.MILVUS_COLLECTION_CONTENTS_V2)

    mock_has.assert_called_once_with(settings.MILVUS_COLLECTION_CONTENTS_V2)
    mock_create.assert_called_once()
    mock_collection.assert_called_once_with(settings.MILVUS_COLLECTION_CONTENTS_V2, using=service._alias)


def test_embedding_dim_tracks_active_embedding_model():
    """MilvusService should canonicalize dimension from EMBEDDING_MODEL."""
    with patch("app.core.milvus_service.settings") as mock_settings:
        mock_settings.MILVUS_HOST = "localhost"
        mock_settings.MILVUS_PORT = 19530
        mock_settings.EMBEDDING_MODEL = "BAAI/bge-m3"
        mock_settings.EMBEDDING_DIMENSION = 2048

        service = MilvusService()

    assert service.embedding_dim == 1024


def test_get_collection_does_not_bootstrap_other_collections():
    """Non-content collections should not trigger v2 bootstrap path."""
    service = MilvusService()
    service._connected = True

    with patch.object(service, "has_collection") as mock_has:
        with patch.object(service, "create_collection_v2") as mock_create:
            with patch("app.core.milvus_service.Collection", return_value=Mock()):
                service.get_collection("paper_images")

    mock_has.assert_not_called()
    mock_create.assert_not_called()


def test_insert_contents_batched_recreates_missing_collection_and_retries():
    """Batch insert should self-heal when Milvus reports missing collection."""
    service = MilvusService()
    service._connected = True

    missing_collection = Mock()
    missing_collection.insert.side_effect = Exception(
        "Collection 'paper_contents_v2' not exist"
    )
    missing_collection.schema.fields = []

    ok_collection = Mock()
    ok_result = Mock()
    ok_result.primary_keys = [123]
    ok_collection.insert.return_value = ok_result
    ok_collection.schema.fields = []

    with patch.object(
        service,
        "get_collection",
        side_effect=[missing_collection, ok_collection, ok_collection, ok_collection],
    ):
        with patch.object(service, "create_collection_v2") as mock_create:
            ids = service.insert_contents_batched(
                [
                    {
                        "paper_id": "p1",
                        "user_id": "u1",
                        "content_type": "text",
                        "page_num": 1,
                        "text": "hello world",
                        "content_data": "hello world",
                            "embedding": [0.1] * service.embedding_dim,
                        "raw_data": {},
                    }
                ],
                batch_size=1,
                max_retries=3,
            )

    assert ids == [123]
    mock_create.assert_called_once()


def test_get_collection_retries_when_constructor_reports_missing_collection():
    """Collection bootstrap should recover from constructor-time missing collection."""
    service = MilvusService()
    service._connected = True

    missing_error = MilvusException(code=1, message="Collection 'paper_contents_v2' not exist")
    recovered_collection = Mock()

    with patch.object(service, "has_collection", return_value=True) as mock_has:
        with patch.object(service, "create_collection_v2") as mock_create:
            with patch(
                "app.core.milvus_service.Collection",
                side_effect=[missing_error, recovered_collection],
            ) as mock_collection:
                collection = service.get_collection(settings.MILVUS_COLLECTION_CONTENTS_V2)

    assert collection is recovered_collection
    mock_has.assert_called_once_with(settings.MILVUS_COLLECTION_CONTENTS_V2)
    mock_create.assert_called_once()
    assert mock_collection.call_count == 2


def test_get_collection_fails_fast_when_embedding_dim_mismatch():
    """Content v2 collection drift should fail fast instead of auto-dropping data."""
    service = MilvusService()
    service._connected = True
    service.embedding_dim = 1024

    mismatched_collection = Mock()
    embedding_field = Mock()
    embedding_field.name = "embedding"
    embedding_field.params = {"dim": 2048}
    mismatched_collection.schema.fields = [embedding_field]

    recreated_collection = Mock()
    recreated_field = Mock()
    recreated_field.name = "embedding"
    recreated_field.params = {"dim": 1024}
    recreated_collection.schema.fields = [recreated_field]

    with patch.object(service, "has_collection", return_value=True):
        with patch.object(service, "drop_collection") as mock_drop:
            with patch.object(service, "create_collection_v2") as mock_create:
                with patch(
                    "app.core.milvus_service.Collection",
                    return_value=mismatched_collection,
                ):
                    with pytest.raises(MilvusCollectionSchemaMismatchError):
                        service.get_collection(settings.MILVUS_COLLECTION_CONTENTS_V2)

    mock_drop.assert_not_called()
    mock_create.assert_not_called()


def test_insert_contents_batched_strict_mode_raises_on_partial_fallback_failure():
    """Strict insert should fail closed when fallback only inserts part of the batch."""
    service = MilvusService()
    service._connected = True

    collection = Mock()
    collection.schema.fields = []
    collection.insert.side_effect = [
        Exception("batch failed"),
        Mock(primary_keys=[101]),
        Exception("row failed"),
    ]

    with patch.object(service, "get_collection", return_value=collection):
        with pytest.raises(MilvusInsertContractError):
            service.insert_contents_batched(
                [
                    {
                        "paper_id": "p1",
                        "user_id": "u1",
                        "content_type": "text",
                        "page_num": 1,
                        "text": "hello world",
                        "content_data": "hello world",
                        "embedding": [0.1] * service.embedding_dim,
                        "raw_data": {},
                    },
                    {
                        "paper_id": "p1",
                        "user_id": "u1",
                        "content_type": "text",
                        "page_num": 2,
                        "text": "second row",
                        "content_data": "second row",
                        "embedding": [0.2] * service.embedding_dim,
                        "raw_data": {},
                    },
                ],
                batch_size=2,
                max_retries=1,
                strict=True,
            )


def test_search_summaries_falls_back_to_query_on_unsupported_field_type():
    """Summary index search should self-heal when Milvus hit parsing fails."""
    service = MilvusService()
    service._connected = True

    mock_collection = Mock()
    mock_collection.search.side_effect = MilvusException(
        code=1,
        message="Unsupported field type: 0",
    )
    mock_collection.query.return_value = [
        {
            "id": 101,
            "paper_id": "paper-1",
            "user_id": "user-1",
            "summary_type": "paper_summary",
            "section_name": "summary",
            "source_chunk_id": "chunk-1",
            "content_data": "summary text",
            "embedding": [1.0, 0.0],
        },
        {
            "id": 102,
            "paper_id": "paper-2",
            "user_id": "user-1",
            "summary_type": "paper_summary",
            "section_name": "summary",
            "source_chunk_id": "chunk-2",
            "content_data": "other summary",
            "embedding": [0.0, 1.0],
        },
    ]

    with patch.object(service, "has_collection", return_value=True):
        with patch.object(service, "get_collection", return_value=mock_collection):
            hits = service.search_summaries(
                embedding=[1.0, 0.0],
                user_id="user-1",
                top_k=1,
            )

    assert len(hits) == 1
    assert hits[0]["paper_id"] == "paper-1"
    assert hits[0]["source_chunk_id"] == "chunk-1"
    assert hits[0]["score"] == 1.0
    mock_collection.query.assert_called_once()
