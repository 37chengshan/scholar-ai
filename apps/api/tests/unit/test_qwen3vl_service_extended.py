"""Extended tests for the real Qwen3VLMultimodalEmbedding implementation."""

from __future__ import annotations

import importlib
import sys

import numpy as np
import pytest
import torch
from PIL import Image
from unittest.mock import MagicMock, patch


def _load_real_qwen3vl_module():
    sys.modules.pop("app.core.qwen3vl_service", None)
    return importlib.import_module("app.core.qwen3vl_service")


class _FakeTensor:
    def __init__(self, values):
        self._values = values

    def cpu(self):
        return self

    def tolist(self):
        return self._values


class _BatchEmbedder:
    def __init__(self):
        self.calls = []

    def process(self, inputs, normalize=True):
        self.calls.append({"inputs": inputs, "normalize": normalize})
        vectors = []
        for idx, _ in enumerate(inputs, start=1):
            vec = np.zeros(2048, dtype=float)
            vec[idx - 1] = 1.0
            vectors.append(vec.tolist())
        return _FakeTensor(vectors)


@pytest.fixture
def qwen_module():
    return _load_real_qwen3vl_module()


@pytest.fixture
def service(qwen_module):
    service = qwen_module.Qwen3VLMultimodalEmbedding(quantization="fp16", device="cpu")
    service.embedder = _BatchEmbedder()
    service._initialized = True
    return service


class TestQwen3VLBatchProcessing:
    def test_encode_text_batch_processing(self, service):
        embeddings = service.encode_text(["文本1", "文本2", "文本3"])

        assert len(embeddings) == 3
        assert all(len(embedding) == 2048 for embedding in embeddings)

    def test_encode_text_batch_normalization(self, service):
        embeddings = service.encode_text(["test1", "test2", "test3"])

        for embedding in embeddings:
            assert 0.99 < np.linalg.norm(embedding) < 1.01

    def test_encode_image_batch(self, service):
        embeddings = service.encode_image(
            [
                Image.new("RGB", (100, 100), color="red"),
                Image.new("RGB", (100, 100), color="blue"),
            ]
        )

        assert len(embeddings) == 2
        assert all(len(embedding) == 2048 for embedding in embeddings)


class TestQwen3VLEmptyInput:
    def test_encode_text_empty_string_uses_null_placeholder(self, service):
        service.encode_text("")
        assert service.embedder.calls[-1]["inputs"] == [{"text": "NULL"}]

    def test_encode_text_empty_list(self, service):
        assert service.encode_text([]) == []

    def test_encode_table_empty(self, service):
        embedding = service.encode_table(caption="", headers=[], rows=[])
        assert len(embedding) == 2048


class TestQwen3VLLargeInput:
    def test_encode_text_very_long_text(self, service):
        long_text = "测试内容 " * 10000
        embedding = service.encode_text(long_text)
        assert len(embedding) == 2048

    def test_encode_table_large(self, service):
        headers = ["Col1", "Col2", "Col3"]
        rows = [{"Col1": f"A{i}", "Col2": f"B{i}", "Col3": f"C{i}"} for i in range(150)]

        embedding = service.encode_table(
            caption="大型测试表格",
            headers=headers,
            rows=rows,
        )

        assert len(embedding) == 2048


class TestQwen3VLQuantization:
    def test_int4_quantization_setting(self, qwen_module):
        service = qwen_module.Qwen3VLMultimodalEmbedding(quantization="int4")
        assert service.quantization == "int4"

    def test_fp16_quantization_setting(self, qwen_module):
        service = qwen_module.Qwen3VLMultimodalEmbedding(quantization="fp16")
        assert service.quantization == "fp16"

    def test_quantization_accepts_any_value(self, qwen_module):
        service = qwen_module.Qwen3VLMultimodalEmbedding(quantization="custom")
        assert service.quantization == "custom"

    def test_load_model_without_embedder_scripts_raises_runtime_error(self, qwen_module):
        service = qwen_module.Qwen3VLMultimodalEmbedding(quantization="fp16")

        with patch.object(qwen_module, "_resolve_embedder_classes", return_value=False):
            with pytest.raises(RuntimeError, match="scripts are unavailable"):
                service.load_model()


class TestQwen3VLDeviceDetection:
    def test_device_auto_detection_cuda(self, qwen_module):
        with patch("torch.cuda.is_available", return_value=True):
            service = qwen_module.Qwen3VLMultimodalEmbedding(device="auto")
            assert service.device == "cuda"

    def test_device_auto_detection_mps(self, qwen_module):
        with patch("torch.cuda.is_available", return_value=False):
            with patch.object(torch.backends, "mps", create=True):
                with patch("torch.backends.mps.is_available", return_value=True):
                    service = qwen_module.Qwen3VLMultimodalEmbedding(device="auto")
                    assert service.device == "mps"

    def test_device_auto_detection_falls_back(self, qwen_module):
        with patch("torch.cuda.is_available", return_value=False):
            fake_mps = MagicMock()
            fake_mps.is_available.return_value = False
            with patch.object(torch.backends, "mps", fake_mps, create=True):
                service = qwen_module.Qwen3VLMultimodalEmbedding(device="auto")
                assert service.device == "cpu"


class TestQwen3VLConcurrency:
    def test_concurrent_text_encoding_shape(self, service):
        results = [service.encode_text(f"并发测试 {i}") for i in range(10)]

        assert len(results) == 10
        assert all(isinstance(result, list) for result in results)
        assert all(len(result) == 2048 for result in results)


class TestQwen3VLErrorHandling:
    def test_encode_without_loading_raises_error(self, qwen_module):
        service = qwen_module.Qwen3VLMultimodalEmbedding()

        with pytest.raises(RuntimeError, match="Model not loaded"):
            service.encode_text("test")

    def test_encode_image_without_loading_raises_error(self, qwen_module):
        service = qwen_module.Qwen3VLMultimodalEmbedding()

        with pytest.raises(RuntimeError, match="Model not loaded"):
            service.encode_image(Image.new("RGB", (100, 100)))


class TestQwen3VLSingleton:
    def test_get_qwen3vl_service_returns_singleton(self, qwen_module):
        qwen_module._qwen3vl_service = None

        with patch.object(qwen_module, "settings") as mock_settings:
            mock_settings.EMBEDDING_QUANTIZATION = "fp16"
            mock_settings.EMBEDDING_DEVICE = "cpu"

            service1 = qwen_module.get_qwen3vl_service()
            service2 = qwen_module.get_qwen3vl_service()

        assert service1 is service2

    @pytest.mark.asyncio
    async def test_create_qwen3vl_service_initializes(self, qwen_module):
        with patch.object(qwen_module, "get_qwen3vl_service") as mock_get:
            mock_instance = MagicMock()
            mock_get.return_value = mock_instance

            service = await qwen_module.create_qwen3vl_service()

            mock_instance.load_model.assert_called_once()
            assert service is mock_instance


class TestQwen3VLModelInfo:
    def test_get_embedding_dim(self, qwen_module):
        service = qwen_module.Qwen3VLMultimodalEmbedding()
        assert service.get_embedding_dim() == 2048

    def test_get_device(self, qwen_module):
        service = qwen_module.Qwen3VLMultimodalEmbedding(device="cpu")
        assert service.get_device() == "cpu"

    def test_is_loaded_initially_false(self, qwen_module):
        service = qwen_module.Qwen3VLMultimodalEmbedding()
        assert service.is_loaded() is False

    def test_is_loaded_true_after_manual_ready_state(self, qwen_module):
        service = qwen_module.Qwen3VLMultimodalEmbedding()
        service._initialized = True
        service.embedder = MagicMock()

        assert service.is_loaded() is True
