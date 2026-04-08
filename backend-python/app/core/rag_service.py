"""DEPRECATED: RAG (Retrieval-Augmented Generation) service.

⚠️ This module is deprecated and will be removed in a future version.

Migration Guide:
- Use MultimodalSearchService instead of RAGService
- All queries should go through unified multimodal search
- PGVector has been removed - all vectors now in Milvus
- Benefits: multimodal search, better reranking, intent detection

See: Phase 04 documentation for migration details.

Provides:
- RAGService: High-level RAG query service (DEPRECATED - uses Milvus)
- retrieve_with_reranking: Milvus search with BGE-Reranker (kept for compatibility)
- Semantic caching for reduced LLM API calls
"""

import warnings

# Emit deprecation warning when module is imported
warnings.warn(
    "RAGService is deprecated. Use MultimodalSearchService instead. "
    "PGVector has been removed - all vectors now in Milvus.",
    DeprecationWarning,
    stacklevel=2,
)

from typing import Any, Dict, List, Optional, Tuple

from app.utils.logger import logger


class RAGService:
    """DEPRECATED: RAG query service with citation-aware answering.

    ⚠️ Use MultimodalSearchService for all queries.
    This class will be removed in v2.0.

    Migration:
        OLD: RAGService().query(question, paper_ids, connection=conn)
        NEW: MultimodalSearchService().search(query, paper_ids, user_id)

    Provides high-level RAG capabilities for answering questions based on
    paper content with proper citation tracking and source attribution.
    Uses Milvus for vector search (PGVector removed).

    Attributes:
        embedding_service: EmbeddingService for query embedding
        semantic_cache: SemanticCache for reducing redundant LLM calls
    """

    def __init__(
        self,
        embedding_service: Optional[Any] = None,
    ):
        """Initialize RAGService.

        Args:
            embedding_service: Optional EmbeddingService instance
        """
        logger.warning(
            "RAGService.__init__ is DEPRECATED. "
            "Use MultimodalSearchService instead."
        )
        self._embedding_service = embedding_service
        # Initialize semantic cache with user decision D-02 settings
        from app.core.semantic_cache import SemanticCache
        self.semantic_cache = SemanticCache(threshold=0.95, ttl=86400)

    @property
    def embedding_service(self) -> Any:
        """Lazy load embedding service."""
        if self._embedding_service is None:
            from app.core.qwen3vl_service import get_qwen3vl_service
            self._embedding_service = get_qwen3vl_service()
        return self._embedding_service

    async def query(
        self,
        question: str,
        paper_ids: List[str],
        user_id: str = "placeholder-user-id",
        top_k: int = 5,
        connection: Optional[Any] = None,  # Kept for API compatibility, not used
    ) -> Dict[str, Any]:
        """Execute RAG query with citations and semantic caching.

        ⚠️ DEPRECATED: Use MultimodalSearchService.search() instead.
        This method will be removed in v2.0.

        Migration:
            OLD: RAGService().query(question, paper_ids, top_k=5)
            NEW: MultimodalSearchService().search(query, paper_ids, user_id, top_k=5)

        Retrieves relevant chunks from Milvus and generates an answer with proper citations.

        Args:
            question: User question
            paper_ids: List of paper UUIDs to search
            user_id: User ID for Milvus filtering
            top_k: Number of chunks to retrieve
            connection: Kept for API compatibility (not used - Milvus only)

        Returns:
            Dictionary with answer, citations, and confidence score
        """
        logger.warning(
            "RAGService.query is DEPRECATED. "
            "Use MultimodalSearchService.search instead."
        )

        if not paper_ids:
            return {
                "answer": "No papers specified for search.",
                "citations": [],
                "confidence": 0.0,
                "cached": False,
            }

        # Check semantic cache first
        cached = await self.semantic_cache.get(question, paper_ids)
        if cached:
            logger.info(
                "Semantic cache hit - returning cached response",
                question=question[:50],
            )
            cached["cached"] = True
            return cached

        # Use Milvus for search (PGVector removed)
        from app.core.milvus_service import get_milvus_service
        from app.core.qwen3vl_service import get_qwen3vl_service

        milvus_service = get_milvus_service()
        qwen3vl_service = get_qwen3vl_service()

        # Generate query embedding (2048-dim Qwen3VL)
        query_embedding = qwen3vl_service.encode_text(question)
        # Ensure we have a single embedding (not a list of embeddings)
        if isinstance(query_embedding[0], list):
            query_embedding = query_embedding[0]  # type: ignore

        # Search Milvus
        results = milvus_service.search_contents(
            embedding=query_embedding,
            user_id=user_id,
            content_type="text",
            top_k=top_k,
        )

        # Filter by paper_ids (only if paper_ids is provided)
        if paper_ids:
            chunks = [r for r in results if r.get("paper_id") in paper_ids]
        else:
            chunks = results  # No filter if paper_ids is empty

        if not chunks:
            return {
                "answer": "No relevant information found in the specified papers.",
                "citations": [],
                "confidence": 0.0,
                "cached": False,
            }

        # Build citations from retrieved chunks
        citations = []
        for chunk in chunks:
            content_data = chunk.get("content_data", "")
            citations.append({
                "text": content_data[:500],  # Preview
                "paper_id": chunk.get("paper_id"),
                "chunk_id": chunk.get("id"),
                "content_preview": content_data[:500],
                "page": chunk.get("page_num"),
                "similarity": 1.0 - chunk.get("distance", 0.0),  # Convert distance to similarity
            })

        # Calculate confidence as average similarity of top results
        avg_similarity = sum(c.get("similarity", 0) for c in citations) / len(citations) if citations else 0
        confidence = min(avg_similarity * 1.2, 1.0)  # Scale up slightly, cap at 1.0

        # Build context-aware answer (simplified)
        context_preview = "\n\n".join([
            f"[Source {i+1}, Page {c['page']}, Score {c['similarity']:.2f}]: {c['text'][:200]}..."
            for i, c in enumerate(citations[:3])
        ])

        answer = (
            f"Based on the retrieved contexts from {len(citations)} sources:\n\n"
            f"{context_preview}\n\n"
            f"(Full LLM integration pending)"
        )

        result = {
            "answer": answer,
            "citations": citations,
            "confidence": round(confidence, 2),
            "cached": False,
        }

        # Cache the result
        await self.semantic_cache.set(question, paper_ids, result)

        logger.info(
            "RAG query completed",
            question=question[:50],
            chunks_retrieved=len(chunks),
            confidence=confidence,
        )

        return result

    async def stream_query(
        self,
        question: str,
        paper_ids: List[str],
        user_id: str = "placeholder-user-id",
        top_k: int = 5,
        connection: Optional[Any] = None,
    ) -> Any:
        """Execute streaming RAG query.

        Generator that yields tokens for SSE streaming response.
        Full implementation would integrate with LiteLLM for token streaming.

        Args:
            question: User question
            paper_ids: List of paper UUIDs to search
            user_id: User ID for Milvus filtering
            top_k: Number of chunks to retrieve
            connection: Kept for API compatibility (not used)

        Yields:
            Token strings for streaming
        """
        # First retrieve contexts
        result = await self.query(
            question=question,
            paper_ids=paper_ids,
            user_id=user_id,
            top_k=top_k,
            connection=connection,
        )

        # Yield answer tokens (word by word)
        words = result["answer"].split()
        for word in words:
            yield word + " "

        # Yield citations marker
        yield "\n\n[CITATIONS]\n"
        for citation in result["citations"]:
            paper_id = citation.get("paper_id", "")[:8]
            yield f"- Paper {paper_id}..., Page {citation['page']}, Score {citation['similarity']:.2f}\n"


# Convenience function for direct usage
async def rag_query(
    question: str,
    paper_ids: List[str],
    user_id: str = "placeholder-user-id",
    top_k: int = 5,
    connection: Optional[Any] = None,
) -> Dict[str, Any]:
    """Execute RAG query with minimal setup.

    Args:
        question: User question
        paper_ids: List of paper UUIDs to search
        user_id: User ID for Milvus filtering
        top_k: Number of chunks to retrieve
        connection: Kept for API compatibility (not used)

    Returns:
        RAG response with answer and citations
    """
    service = RAGService()
    return await service.query(
        question=question,
        paper_ids=paper_ids,
        user_id=user_id,
        top_k=top_k,
        connection=connection,
    )


async def retrieve_with_reranking(
    query: str,
    user_id: str,
    paper_ids: Optional[List[str]] = None,
    top_k: int = 20,
    rerank_top_n: int = 5
) -> List[Dict[str, Any]]:
    """Retrieve chunks with reranking per D-02.

    Performs initial Milvus search and reranks results using BGE-Reranker-large.

    Args:
        query: Search query
        user_id: User ID for filtering
        paper_ids: Optional paper IDs to filter
        top_k: Initial retrieval candidates (default 20 per D-02)
        rerank_top_n: Number of results after reranking (default 5 per D-02)

    Returns:
        List of chunks with rerank_score field
    """
    from app.core.milvus_service import get_milvus_service
    from app.core.qwen3vl_service import get_qwen3vl_service
    from app.core.reranker_service import get_reranker_service

    # Get singleton instances
    milvus_service = get_milvus_service()
    qwen3vl_service = get_qwen3vl_service()
    reranker_service = get_reranker_service()

    # Step 1: Generate query embedding (2048-dim Qwen3VL)
    query_embedding = qwen3vl_service.encode_text(query)
    # Ensure we have a single embedding (not a list of embeddings)
    if isinstance(query_embedding[0], list):
        query_embedding = query_embedding[0]  # type: ignore

    # Step 2: Search Milvus
    initial_results = milvus_service.search_contents(
        embedding=query_embedding,  # type: ignore
        user_id=user_id,
        content_type="text",
        top_k=top_k
    )

    # Filter by paper_ids if provided
    if paper_ids:
        initial_results = [r for r in initial_results if r.get("paper_id") in paper_ids]

    if not initial_results:
        return []

    # Step 3: Reranking (per D-02)
    documents = [r.get("content_data", "") for r in initial_results]

    reranked = reranker_service.rerank(
        query=query,
        documents=documents,
        top_k=rerank_top_n
    )

    # Step 4: Build final results with rerank scores
    # reranked is List[Tuple[document, score]]
    final_results = []
    for doc, score in reranked:
        # Find the original result by document content
        for r in initial_results:
            if r.get("content_data", "") == doc:
                r["rerank_score"] = score
                final_results.append(r)
                break

    return final_results