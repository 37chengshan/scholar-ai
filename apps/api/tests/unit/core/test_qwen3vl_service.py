"""Unit tests for the real Qwen3VLMultimodalEmbedding implementation.

These tests bypass the global conftest mock for ``app.core.qwen3vl_service`` and
verify the current concrete contract with a local fake embedder instead of
trying to load model weights.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image


def _load_real_qwen3vl_module():
    """Import the real qwen3vl_service module, bypassing test-global mocks."""
    sys.modules.pop("app.core.qwen3vl_service", None)
    return importlib.import_module("app.core.qwen3vl_service")


class _FakeTensor:
    def __init__(self, values):
        self._values = values

    def cpu(self):
        return self

    def tolist(self):
        return self._values


class _FakeEmbedder:
    def __init__(self):
        self.calls = []

    def process(self, inputs, normalize=True):
        self.calls.append({"inputs": inputs, "normalize": normalize})

        dim = 2048
        base = np.zeros(dim, dtype=float)
        base[0] = 1.0
        vectors = [base.tolist() for _ in inputs]
        return _FakeTensor(vectors)


@pytest.fixture
def qwen_module():
    return _load_real_qwen3vl_module()


@pytest.fixture
def service(qwen_module):
    service = qwen_module.Qwen3VLMultimodalEmbedding(quantization="fp16", device="cpu")
    service.embedder = _FakeEmbedder()
    service._initialized = True
    return service


class TestQwen3VLMultimodalEmbedding:
    def test_encode_image_returns_2048_dim_vector(self, service):
        embedding = service.encode_image(Image.new("RGB", (32, 32), color="red"))

        assert isinstance(embedding, list)
        assert len(embedding) == 2048
        assert all(isinstance(x, float) for x in embedding)

    def test_encode_image_vector_is_normalized(self, service):
        embedding = service.encode_image(Image.new("RGB", (32, 32), color="red"))

        norm = np.linalg.norm(embedding)
        assert 0.99 < norm < 1.01

    def test_encode_text_returns_2048_dim_vector(self, service):
        embedding = service.encode_text("This is a test sentence for embedding.")

        assert isinstance(embedding, list)
        assert len(embedding) == 2048
        assert all(isinstance(x, float) for x in embedding)

    def test_encode_text_vector_is_normalized(self, service):
        embedding = service.encode_text("Another test sentence.")

        norm = np.linalg.norm(embedding)
        assert 0.99 < norm < 1.01

    def test_encode_table_returns_2048_dim_vector(self, service):
        embedding = service.encode_table(
            caption="Experimental Results",
            headers=["Method", "Accuracy"],
            rows=[{"Method": "Baseline", "Accuracy": "85.2%"}],
        )

        assert isinstance(embedding, list)
        assert len(embedding) == 2048
        assert all(isinstance(x, float) for x in embedding)

    def test_encode_table_vector_is_normalized(self, service):
        embedding = service.encode_table(
            caption="Experimental Results",
            headers=["Method", "Accuracy"],
            rows=[{"Method": "Baseline", "Accuracy": "85.2%"}],
        )

        norm = np.linalg.norm(embedding)
        assert 0.99 < norm < 1.01

    def test_encode_text_batch_returns_list_of_vectors(self, service):
        embeddings = service.encode_text(
            ["First test sentence.", "Second test sentence.", "Third test sentence."]
        )

        assert isinstance(embeddings, list)
        assert len(embeddings) == 3
        assert all(len(embedding) == 2048 for embedding in embeddings)
        assert all(0.99 < np.linalg.norm(embedding) < 1.01 for embedding in embeddings)

    def test_encode_image_from_path(self, service, tmp_path):
        image_path = tmp_path / "sample.png"
        Image.new("RGB", (24, 24), color="blue").save(image_path)

        embedding = service.encode_image(str(image_path))

        assert len(embedding) == 2048
        assert 0.99 < np.linalg.norm(embedding) < 1.01

    def test_encode_image_passes_image_inputs_to_embedder(self, service):
        image = Image.new("RGB", (16, 16), color="green")

        service.encode_image(image)

        assert service.embedder.calls[-1]["inputs"] == [{"image": image}]
        assert service.embedder.calls[-1]["normalize"] is True

    def test_encode_text_normalizes_empty_string_to_null_placeholder(self, service):
        service.encode_text("")

        assert service.embedder.calls[-1]["inputs"] == [{"text": "NULL"}]

    def test_encode_text_empty_list_returns_empty_list(self, service):
        assert service.encode_text([]) == []

    def test_encode_text_single_none_returns_empty_list(self, service):
        assert service.encode_text(None) == []

    def test_model_path_comes_from_settings(self, qwen_module):
        assert hasattr(qwen_module.settings, "QWEN3VL_EMBEDDING_MODEL_PATH")
        assert qwen_module.settings.QWEN3VL_EMBEDDING_MODEL_PATH

    def test_embedding_dim_is_2048(self, qwen_module):
        assert qwen_module.Qwen3VLMultimodalEmbedding.EMBEDDING_DIM == 2048


class TestQwen3VLDeviceDetection:
    def test_detect_device_auto(self, qwen_module):
        service = qwen_module.Qwen3VLMultimodalEmbedding(device="auto")
        assert service.device in ["cuda", "mps", "cpu"]

    def test_detect_device_cuda_if_available(self, qwen_module):
        import torch

        if torch.cuda.is_available():
            service = qwen_module.Qwen3VLMultimodalEmbedding(device="auto")
            assert service.device == "cuda"

    def test_detect_device_mps_if_available(self, qwen_module):
        import torch

        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            service = qwen_module.Qwen3VLMultimodalEmbedding(device="auto")
            assert service.device == "mps"


class TestQwen3VLTableSerialization:
    def test_table_serialization_format(self, qwen_module):
        service = qwen_module.Qwen3VLMultimodalEmbedding(quantization="fp16")

        serialized = service._serialize_table(
            "Test Table",
            ["A", "B", "C"],
            [{"A": 1, "B": 2, "C": 3}],
        )

        assert "Table: Test Table" in serialized
        assert "Columns: A, B, C" in serialized
        assert "Sample data:" in serialized

    def test_table_serialization_truncates_rows(self, qwen_module):
        service = qwen_module.Qwen3VLMultimodalEmbedding(quantization="fp16")

        serialized = service._serialize_table(
            "Test",
            ["col"],
            [{"col": f"row{i}"} for i in range(5)],
        )

        assert "row0" in serialized
        assert "row1" in serialized
        assert "row2" in serialized
        assert "row3" not in serialized
        assert "row4" not in serialized
