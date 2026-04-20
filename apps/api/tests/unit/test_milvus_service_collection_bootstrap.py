"""Regression tests for MilvusService collection bootstrap behavior."""

from unittest.mock import Mock, patch

from pymilvus.exceptions import MilvusException

from app.core.milvus_service import MilvusService
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

    ok_collection = Mock()
    ok_result = Mock()
    ok_result.primary_keys = [123]
    ok_collection.insert.return_value = ok_result

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
                        "embedding": [0.1, 0.2, 0.3],
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
