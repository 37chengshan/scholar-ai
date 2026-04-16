"""Deprecated import shim for RAG schemas.

Use app.schemas.rag for new imports.
"""

from app.schemas.rag import Citation, RAGQueryRequest, RAGQueryResult, RAGResponse, RAGStreamChunk

__all__ = [
    "Citation",
    "RAGQueryRequest",
    "RAGResponse",
    "RAGStreamChunk",
    "RAGQueryResult",
]
