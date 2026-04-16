"""Integration tests for Milvus collections.

These tests require a running Milvus instance.
Skip if Milvus is not available.
"""

import pytest
import random
from typing import List

from app.core.milvus_service import MilvusService, get_milvus_service


def generate_random_embedding(dim: int = 768) -> List[float]:
    """Generate random normalized embedding."""
    import math
    vec = [random.random() for _ in range(dim)]
    # Normalize
    norm = math.sqrt(sum(x * x for x in vec))
    return [x / norm for x in vec]


@pytest.fixture(scope="module")
def milvus_service():
    """Create Milvus service for tests."""
    service = MilvusService()
    try:
        service.connect()
        yield service
    except Exception as e:
        pytest.skip(f"Milvus not available: {e}")
    finally:
        service.disconnect()


class TestMilvusCollections:
    """Test Milvus collection operations."""

    def test_connection(self, milvus_service):
        """Test that Milvus connection works."""
        assert milvus_service.is_connected()

    def test_create_collections(self, milvus_service):
        """Test creating collections."""
        # This will create or get existing collections
        collections = milvus_service.create_collections()

        assert "paper_images" in collections
        assert "paper_tables" in collections

        # Verify collections are loaded
        for name, collection in collections.items():
            assert collection is not None
            assert collection.name in ["paper_images", "paper_tables"]

    def test_insert_and_search_images(self, milvus_service):
        """Test inserting and searching images."""
        milvus_service.create_collections()

        # Insert test images
        test_data = [
            {
                "paper_id": "test-paper-001",
                "user_id": "test-user",
                "page_num": 1,
                "caption": "Test figure 1",
                "image_type": "figure",
                "embedding": generate_random_embedding(),
                "bbox": {"x": 0, "y": 0, "w": 100, "h": 100},
            },
            {
                "paper_id": "test-paper-001",
                "user_id": "test-user",
                "page_num": 2,
                "caption": "Test chart",
                "image_type": "chart",
                "embedding": generate_random_embedding(),
                "bbox": {"x": 0, "y": 0, "w": 200, "h": 150},
            },
        ]

        ids = milvus_service.insert_images(test_data)
        assert len(ids) == 2

        # Search using the first embedding
        results = milvus_service.search_images(
            embedding=test_data[0]["embedding"],
            user_id="test-user",
            top_k=5
        )

        assert len(results) >= 1
        # First result should be the query itself
        assert results[0]["distance"] > 0.99  # Very close match

    def test_insert_and_search_tables(self, milvus_service):
        """Test inserting and searching tables."""
        milvus_service.create_collections()

        # Insert test tables
        test_data = [
            {
                "paper_id": "test-paper-002",
                "user_id": "test-user",
                "page_num": 3,
                "table_data": {"headers": ["A", "B"], "rows": [[1, 2]]},
                "description": "Results table",
                "embedding": generate_random_embedding(),
            },
        ]

        ids = milvus_service.insert_tables(test_data)
        assert len(ids) == 1

        # Search
        results = milvus_service.search_tables(
            embedding=test_data[0]["embedding"],
            user_id="test-user",
            top_k=5
        )

        assert len(results) >= 1
        assert results[0]["distance"] > 0.99

    def test_user_filtering(self, milvus_service):
        """Test that user_id filtering works."""
        milvus_service.create_collections()

        # Insert data for different users
        user1_data = {
            "paper_id": "test-paper-003",
            "user_id": "user-1",
            "page_num": 1,
            "caption": "User 1 image",
            "image_type": "figure",
            "embedding": generate_random_embedding(),
            "bbox": {},
        }
        user2_data = {
            "paper_id": "test-paper-004",
            "user_id": "user-2",
            "page_num": 1,
            "caption": "User 2 image",
            "image_type": "figure",
            "embedding": generate_random_embedding(),
            "bbox": {},
        }

        milvus_service.insert_images([user1_data, user2_data])

        # Search as user-1
        results = milvus_service.search_images(
            embedding=user1_data["embedding"],
            user_id="user-1",
            top_k=5
        )

        # All results should be from user-1
        for result in results:
            assert result["paper_id"] == "test-paper-003"

    def test_delete_by_paper(self, milvus_service):
        """Test deleting vectors by paper_id."""
        milvus_service.create_collections()

        # Insert data
        test_data = {
            "paper_id": "test-paper-delete",
            "user_id": "test-user",
            "page_num": 1,
            "caption": "To be deleted",
            "image_type": "figure",
            "embedding": generate_random_embedding(),
            "bbox": {},
        }

        milvus_service.insert_images([test_data])

        # Delete
        milvus_service.delete_by_paper("test-paper-delete")

        # Search should return empty
        results = milvus_service.search_images(
            embedding=test_data["embedding"],
            user_id="test-user",
            top_k=5
        )

        # Should not find the deleted paper
        paper_ids = [r["paper_id"] for r in results]
        assert "test-paper-delete" not in paper_ids
