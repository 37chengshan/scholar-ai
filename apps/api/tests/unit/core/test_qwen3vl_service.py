"""Unit tests for Qwen3VLMultimodalEmbedding service.

Tests:
- encode_image returns 2048-dim vector for PIL.Image input
- encode_text returns 2048-dim vector for string input
- encode_table returns 2048-dim vector for table dict input
- embeddings are normalized (unit vectors, COSINE distance)
"""

import pytest
from PIL import Image
import numpy as np

from app.core.qwen3vl_service import Qwen3VLMultimodalEmbedding


# Global service instance (load once for all tests)
_service_instance = None


def get_test_service():
    """Get or create test service instance (singleton)."""
    global _service_instance
    if _service_instance is None:
        _service_instance = Qwen3VLMultimodalEmbedding(quantization="fp16", device="auto")
        _service_instance.load_model()
    return _service_instance


class TestQwen3VLMultimodalEmbedding:
    """Tests for Qwen3VL multimodal embedding service."""

    @pytest.fixture(scope="class")
    def service(self):
        """Create service instance for testing (singleton, loaded once)."""
        return get_test_service()

    @pytest.fixture
    def test_image(self):
        """Create test PIL.Image."""
        return Image.new("RGB", (100, 100), color="red")

    @pytest.fixture
    def test_table_data(self):
        """Create test table data."""
        return {
            "caption": "Experimental Results",
            "headers": ["Method", "Accuracy", "Speed"],
            "rows": [
                {"Method": "Baseline", "Accuracy": "85.2%", "Speed": "120ms"},
                {"Method": "Proposed", "Accuracy": "92.1%", "Speed": "95ms"},
            ]
        }

    def test_encode_image_returns_2048_dim_vector(self, service, test_image):
        """Test 1: encode_image returns 2048-dim vector for PIL.Image input."""
        embedding = service.encode_image(test_image)

        # Verify dimension
        assert len(embedding) == 2048
        assert isinstance(embedding, list)
        assert all(isinstance(x, float) for x in embedding)

    def test_encode_image_vector_is_normalized(self, service, test_image):
        """Test 4: embeddings are normalized (unit vectors, COSINE distance)."""
        embedding = service.encode_image(test_image)

        # Verify normalization (unit vector)
        norm = np.linalg.norm(embedding)
        assert 0.99 < norm < 1.01, f"Vector norm should be ~1.0, got {norm}"

    def test_encode_text_returns_2048_dim_vector(self, service):
        """Test 2: encode_text returns 2048-dim vector for string input."""
        text = "This is a test sentence for embedding."
        embedding = service.encode_text(text)

        # Verify dimension
        assert len(embedding) == 2048
        assert isinstance(embedding, list)
        assert all(isinstance(x, float) for x in embedding)

    def test_encode_text_vector_is_normalized(self, service):
        """Test 4: text embeddings are normalized."""
        text = "Another test sentence."
        embedding = service.encode_text(text)

        # Verify normalization
        norm = np.linalg.norm(embedding)
        assert 0.99 < norm < 1.01, f"Vector norm should be ~1.0, got {norm}"

    def test_encode_table_returns_2048_dim_vector(self, service, test_table_data):
        """Test 3: encode_table returns 2048-dim vector for table dict input."""
        embedding = service.encode_table(
            caption=test_table_data["caption"],
            headers=test_table_data["headers"],
            rows=test_table_data["rows"]
        )

        # Verify dimension
        assert len(embedding) == 2048
        assert isinstance(embedding, list)
        assert all(isinstance(x, float) for x in embedding)

    def test_encode_table_vector_is_normalized(self, service, test_table_data):
        """Test 4: table embeddings are normalized."""
        embedding = service.encode_table(
            caption=test_table_data["caption"],
            headers=test_table_data["headers"],
            rows=test_table_data["rows"]
        )

        # Verify normalization
        norm = np.linalg.norm(embedding)
        assert 0.99 < norm < 1.01, f"Vector norm should be ~1.0, got {norm}"

    def test_encode_text_batch_returns_list_of_vectors(self, service):
        """Test batch encoding returns list of 2048-dim vectors."""
        texts = [
            "First test sentence.",
            "Second test sentence.",
            "Third test sentence."
        ]
        embeddings = service.encode_text(texts)

        # Verify batch output
        assert isinstance(embeddings, list)
        assert len(embeddings) == 3
        for emb in embeddings:
            assert len(emb) == 2048
            norm = np.linalg.norm(emb)
            assert 0.99 < norm < 1.01

    def test_encode_image_from_path(self, service):
        """Test encode_image accepts file path string."""
        # Create a temporary test image
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            test_image = Image.new("RGB", (50, 50), color="blue")
            test_image.save(f.name)
            temp_path = f.name

        try:
            embedding = service.encode_image(temp_path)
            assert len(embedding) == 2048
            norm = np.linalg.norm(embedding)
            assert 0.99 < norm < 1.01
        finally:
            os.unlink(temp_path)

    def test_model_path_is_local(self, service):
        """Test that MODEL_PATH uses local path per D-01."""
        assert service.MODEL_PATH == "./Qwen/Qwen3-VL-Embedding-2B"

    def test_embedding_dim_is_2048(self, service):
        """Test EMBEDDING_DIM is 2048."""
        assert service.EMBEDDING_DIM == 2048


class TestQwen3VLDeviceDetection:
    """Tests for device auto-detection."""

    def test_detect_device_auto(self):
        """Test device detection with 'auto' parameter."""
        service = Qwen3VLMultimodalEmbedding(device="auto")
        # Should detect available device
        assert service.device in ["cuda", "mps", "cpu"]

    def test_detect_device_cuda_if_available(self):
        """Test CUDA detection."""
        import torch
        if torch.cuda.is_available():
            service = Qwen3VLMultimodalEmbedding(device="auto")
            assert service.device == "cuda"

    def test_detect_device_mps_if_available(self):
        """Test MPS (M1 Pro) detection."""
        import torch
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            service = Qwen3VLMultimodalEmbedding(device="auto")
            assert service.device == "mps"


class TestQwen3VLTableSerialization:
    """Tests for table serialization format per D-02."""

    def test_table_serialization_format(self):
        """Test table serialization format matches D-02 specification."""
        service = Qwen3VLMultimodalEmbedding(quantization="fp16")

        # Expected format: "Table: {caption}\nColumns: {headers}\nSample data: {rows}"
        caption = "Test Table"
        headers = ["A", "B", "C"]
        rows = [{"A": 1, "B": 2, "C": 3}]

        serialized = service._serialize_table(caption, headers, rows)

        assert "Table: Test Table" in serialized
        assert "Columns: A, B, C" in serialized
        assert "Sample data:" in serialized

    def test_table_serialization_truncates_rows(self):
        """Test table serialization truncates to max 3 rows."""
        service = Qwen3VLMultimodalEmbedding(quantization="fp16")

        # Create 5 rows
        rows = [
            {"col": f"row{i}"} for i in range(5)
        ]

        serialized = service._serialize_table("Test", ["col"], rows)

        # Should only include first 3 rows
        assert "row0" in serialized
        assert "row1" in serialized
        assert "row2" in serialized
        assert "row3" not in serialized
        assert "row4" not in serialized