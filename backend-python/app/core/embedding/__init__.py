"""Embedding services module.

Provides:
- BaseEmbeddingService abstract interface
- BGEEmbeddingService adapter (text-only, 1024-dim)
- Qwen3VLEmbeddingService adapter (multimodal, 2048-dim)
- EmbeddingServiceFactory for configuration-driven selection
- Backward compatible get_embedding_service() function

Design decisions (per D-01, D-02):
- Factory pattern for dynamic instantiation
- Configuration via environment variables (EMBEDDING_MODEL)
- Caching for memory efficiency
- Default to Qwen3-VL for multimodal support
"""

from app.core.embedding.base import BaseEmbeddingService
from app.core.embedding.bge_embedding import BGEEmbeddingService
from app.core.embedding.qwen3vl_embedding import Qwen3VLEmbeddingService
from app.core.embedding.factory import EmbeddingServiceFactory, get_embedding_service

__all__ = [
    "BaseEmbeddingService",
    "BGEEmbeddingService",
    "Qwen3VLEmbeddingService",
    "EmbeddingServiceFactory",
    "get_embedding_service",
]