"""Embedding services module.

Provides:
- BaseEmbeddingService abstract interface
- BGEEmbeddingService adapter (text-only, 1024-dim) - Task 2
- Qwen3VLEmbeddingService adapter (multimodal, 2048-dim) - Task 3
- EmbeddingServiceFactory for configuration-driven selection - Task 4

Design decisions (per D-01, D-02):
- Factory pattern for dynamic instantiation
- Configuration via environment variables (EMBEDDING_MODEL)
- Caching for memory efficiency
- Default to Qwen3-VL for multimodal support
"""

# Import only what exists right now (Task 1 complete)
from app.core.embedding.base import BaseEmbeddingService

# Will be added in subsequent tasks:
# from app.core.embedding.bge_embedding import BGEEmbeddingService
# from app.core.embedding.qwen3vl_embedding import Qwen3VLEmbeddingService
# from app.core.embedding.factory import EmbeddingServiceFactory, get_embedding_service

__all__ = [
    "BaseEmbeddingService",
    # Will be added in subsequent tasks:
    # "BGEEmbeddingService",
    # "Qwen3VLEmbeddingService",
    # "EmbeddingServiceFactory",
    # "get_embedding_service",
]