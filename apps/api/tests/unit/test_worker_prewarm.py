from unittest.mock import Mock, patch

from app.core.celery_config import _prewarm_worker_runtime


def test_prewarm_worker_runtime_initializes_docling_embedding_and_milvus():
    parser = Mock()
    embedding_service = Mock()
    milvus_service = Mock()

    with patch("app.core.docling_service.get_docling_parser", return_value=parser), patch(
        "app.core.qwen3vl_service.get_qwen3vl_service", return_value=embedding_service
    ), patch("app.core.milvus_service.get_milvus_service", return_value=milvus_service):
        _prewarm_worker_runtime()

    parser.prewarm.assert_called_once_with()
    embedding_service.load_model.assert_called_once_with()
    embedding_service.warmup_text_encode.assert_called_once_with()
    milvus_service.connect.assert_called_once_with()
    milvus_service.create_collections.assert_called_once_with()
