"""Unit tests for page clustering using the current async embedding contract."""

from unittest.mock import Mock, patch

import pytest

from app.core.page_clustering import cluster_pages


class TestPageClustering:
    @pytest.mark.asyncio
    async def test_cluster_single_result_returns_single_cluster(self):
        results = [
            {
                "id": "chunk-1",
                "paper_id": "paper-1",
                "page_num": 1,
                "content_data": "This is a test content about machine learning.",
            }
        ]

        clusters = await cluster_pages(results, threshold=0.8)

        assert clusters == {0: results}

    @pytest.mark.asyncio
    async def test_cluster_similar_pages_groups_together(self):
        results = [
            {
                "id": "chunk-1",
                "paper_id": "paper-1",
                "page_num": 1,
                "content_data": "Introduction to deep learning and neural networks.",
            },
            {
                "id": "chunk-2",
                "paper_id": "paper-1",
                "page_num": 2,
                "content_data": "Deep learning neural networks architecture details.",
            },
            {
                "id": "chunk-3",
                "paper_id": "paper-1",
                "page_num": 3,
                "content_data": "Deep learning neural networks training process.",
            },
        ]

        with patch("app.core.page_clustering.get_embedding_service") as mock_factory:
            mock_service = Mock()
            mock_service.encode_text.return_value = [
                [0.9, 0.1, 0.0],
                [0.88, 0.12, 0.0],
                [0.87, 0.13, 0.0],
            ]
            mock_factory.return_value = mock_service

            clusters = await cluster_pages(results, threshold=0.8)

        assert len(clusters) == 1
        assert sum(len(items) for items in clusters.values()) == 3

    @pytest.mark.asyncio
    async def test_cluster_diverse_pages_creates_multiple_clusters(self):
        results = [
            {
                "id": "chunk-1",
                "paper_id": "paper-1",
                "page_num": 1,
                "content_data": "Introduction to machine learning.",
            },
            {
                "id": "chunk-2",
                "paper_id": "paper-1",
                "page_num": 5,
                "content_data": "Experimental results and performance metrics.",
            },
            {
                "id": "chunk-3",
                "paper_id": "paper-1",
                "page_num": 10,
                "content_data": "Conclusion and future work directions.",
            },
            {
                "id": "chunk-4",
                "paper_id": "paper-1",
                "page_num": 11,
                "content_data": "References and bibliography.",
            },
        ]

        with patch("app.core.page_clustering.get_embedding_service") as mock_factory:
            mock_service = Mock()
            mock_service.encode_text.return_value = [
                [1.0, 0.0, 0.0, 0.0],
                [0.0, 1.0, 0.0, 0.0],
                [0.0, 0.0, 1.0, 0.0],
                [0.0, 0.0, 0.0, 1.0],
            ]
            mock_factory.return_value = mock_service

            clusters = await cluster_pages(results, threshold=0.5)

        assert len(clusters) >= 2
        assert sum(len(items) for items in clusters.values()) == 4

    @pytest.mark.asyncio
    async def test_cluster_threshold_affects_cluster_count(self):
        results = [
            {"id": "chunk-1", "paper_id": "paper-1", "page_num": 1, "content_data": "Introduction section."},
            {"id": "chunk-2", "paper_id": "paper-1", "page_num": 2, "content_data": "Introduction continued."},
            {"id": "chunk-3", "paper_id": "paper-1", "page_num": 3, "content_data": "Method section."},
            {"id": "chunk-4", "paper_id": "paper-1", "page_num": 4, "content_data": "Results section."},
        ]

        with patch("app.core.page_clustering.get_embedding_service") as mock_factory:
            mock_service = Mock()
            mock_service.encode_text.return_value = [
                [1.0, 0.0, 0.0, 0.0],
                [0.95, 0.05, 0.0, 0.0],
                [0.0, 1.0, 0.0, 0.0],
                [0.0, 0.0, 1.0, 0.0],
            ]
            mock_factory.return_value = mock_service

            clusters_high = await cluster_pages(results, threshold=0.95)
            clusters_low = await cluster_pages(results, threshold=0.3)

        assert sum(len(items) for items in clusters_high.values()) == 4
        assert sum(len(items) for items in clusters_low.values()) == 4
        assert len(clusters_low) <= len(clusters_high)

    @pytest.mark.asyncio
    async def test_cluster_empty_results(self):
        assert await cluster_pages([], threshold=0.8) == {}

    @pytest.mark.asyncio
    async def test_cluster_two_results_returns_single_cluster(self):
        results = [
            {"id": "chunk-1", "paper_id": "paper-1", "page_num": 1, "content_data": "Content 1"},
            {"id": "chunk-2", "paper_id": "paper-1", "page_num": 2, "content_data": "Content 2"},
        ]

        clusters = await cluster_pages(results, threshold=0.8)

        assert clusters == {0: results}
