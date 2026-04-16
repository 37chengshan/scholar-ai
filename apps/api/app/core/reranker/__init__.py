"""Reranker module with modular, swappable architecture.

Provides:
- BaseRerankerService abstract interface
- BGERerankerService adapter (text-only)
- Qwen3VLRerankerService adapter (multimodal)
- RerankerServiceFactory for dynamic instantiation
- Configuration-driven model selection

Usage:
    from app.core.reranker.factory import get_reranker_service
    
    # Get reranker (configured via RERANKER_MODEL env var)
    reranker = get_reranker_service()
    reranker.load_model()
    
    # Rerank documents
    results = reranker.rerank(query, documents, top_k=10)
"""

from app.core.reranker.base import BaseRerankerService

__all__ = ["BaseRerankerService"]