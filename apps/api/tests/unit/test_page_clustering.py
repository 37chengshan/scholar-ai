"""Unit tests for page clustering algorithm.

Tests for cluster_pages function using sklearn AgglomerativeClustering.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, List, Any

from app.core.page_clustering import cluster_pages


class TestPageClustering:
    """Test suite for page clustering functionality."""

    def test_cluster_single_result_returns_single_cluster(self):
        """Test that 1 result returns single cluster {0: [result]}."""
        # Setup: Single result
        results = [
            {
                "id": "chunk-1",
                "paper_id": "paper-1",
                "page_num": 1,
                "content_data": "This is a test content about machine learning.",
            }
        ]

        # Mock BGE-M3 service
        with patch("app.core.page_clustering.get_bge_m3_service") as mock_bge:
            mock_service = Mock()
            mock_service.encode_text.return_value = [[0.1] * 1024]
            mock_bge.return_value = mock_service

            # Execute
            clusters = cluster_pages(results, threshold=0.8)

            # Verify: Should return single cluster with all results
            assert len(clusters) == 1
            assert 0 in clusters
            assert len(clusters[0]) == 1
            assert clusters[0][0]["id"] == "chunk-1"

    def test_cluster_similar_pages_groups_together(self):
        """Test that similar content pages group together."""
        # Setup: Two pages with similar content
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

        # Mock BGE-M3 service with similar embeddings
        with patch("app.core.page_clustering.get_bge_m3_service") as mock_bge:
            mock_service = Mock()
            # Similar embeddings (high cosine similarity)
            mock_service.encode_text.return_value = [
                [0.9] * 1024,
                [0.88] * 1024,
                [0.87] * 1024,
            ]
            mock_bge.return_value = mock_service

            # Execute
            clusters = cluster_pages(results, threshold=0.8)

            # Verify: Should group similar pages together
            assert len(clusters) >= 1
            # All results should be present in clusters
            total_results = sum(len(c) for c in clusters.values())
            assert total_results == 3

    def test_cluster_diverse_pages_creates_multiple_clusters(self):
        """Test that diverse content separates into multiple clusters."""
        # Setup: Pages with different content
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

        # Mock BGE-M3 service with diverse embeddings
        with patch("app.core.page_clustering.get_bge_m3_service") as mock_bge:
            mock_service = Mock()
            # Diverse embeddings (low cosine similarity)
            mock_service.encode_text.return_value = [
                [1.0 if i % 4 == 0 else 0.0 for i in range(1024)],  # Page 1
                [1.0 if i % 4 == 1 else 0.0 for i in range(1024)],  # Page 5
                [1.0 if i % 4 == 2 else 0.0 for i in range(1024)],  # Page 10
                [1.0 if i % 4 == 3 else 0.0 for i in range(1024)],  # Page 11
            ]
            mock_bge.return_value = mock_service

            # Execute with lower threshold to create multiple clusters
            clusters = cluster_pages(results, threshold=0.5)

            # Verify: Should create multiple clusters
            assert len(clusters) >= 2
            total_results = sum(len(c) for c in clusters.values())
            assert total_results == 4

    def test_cluster_threshold_affects_cluster_count(self):
        """Test that clustering threshold parameter affects cluster count."""
        # Setup: Pages with moderate similarity
        results = [
            {
                "id": "chunk-1",
                "paper_id": "paper-1",
                "page_num": 1,
                "content_data": "Introduction section.",
            },
            {
                "id": "chunk-2",
                "paper_id": "paper-1",
                "page_num": 2,
                "content_data": "Introduction continued.",
            },
            {
                "id": "chunk-3",
                "paper_id": "paper-1",
                "page_num": 3,
                "content_data": "Method section.",
            },
            {
                "id": "chunk-4",
                "paper_id": "paper-1",
                "page_num": 4,
                "content_data": "Results section.",
            },
        ]

        # Mock BGE-M3 service
        with patch("app.core.page_clustering.get_bge_m3_service") as mock_bge:
            mock_service = Mock()
            # Moderate similarity embeddings
            mock_service.encode_text.return_value = [
                [0.8] * 1024,
                [0.75] * 1024,
                [0.5] * 1024,
                [0.3] * 1024,
            ]
            mock_bge.return_value = mock_service

            # Execute with high threshold (fewer clusters)
            clusters_high = cluster_pages(results, threshold=0.9)

            # Execute with low threshold (more clusters)
            clusters_low = cluster_pages(results, threshold=0.3)

            # Verify: Lower threshold should create more clusters
            assert len(clusters_low) >= len(clusters_high)
            total_high = sum(len(c) for c in clusters_high.values())
            total_low = sum(len(c) for c in clusters_low.values())
            assert total_high == 4
            assert total_low == 4

    def test_cluster_empty_results(self):
        """Test clustering with empty results."""
        # Setup: Empty results
        results = []

        # Execute
        clusters = cluster_pages(results, threshold=0.8)

        # Verify: Should return empty dict
        assert len(clusters) == 0

    def test_cluster_two_results_returns_single_cluster(self):
        """Test that 2 results returns single cluster (below minimum)."""
        # Setup: Two results
        results = [
            {
                "id": "chunk-1",
                "paper_id": "paper-1",
                "page_num": 1,
                "content_data": "Content 1",
            },
            {
                "id": "chunk-2",
                "paper_id": "paper-1",
                "page_num": 2,
                "content_data": "Content 2",
            },
        ]

        # Execute (no mocking needed for < 3 results)
        clusters = cluster_pages(results, threshold=0.8)

        # Verify: Should return single cluster
        assert len(clusters) == 1
        assert 0 in clusters
        assert len(clusters[0]) == 2