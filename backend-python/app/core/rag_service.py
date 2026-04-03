"""DEPRECATED: RAG (Retrieval-Augmented Generation) service with PaperQA2 integration.

⚠️ This module is deprecated and will be removed in a future version.

Migration Guide:
- Use MultimodalSearchService instead of RAGService
- All queries should go through unified multimodal search
- PGVector is replaced by Milvus for vector storage
- Benefits: multimodal search, better reranking, intent detection

See: Phase 04 documentation for migration details.

Provides:
- PGVectorStore: Custom vector store for PaperQA2 using existing PGVector infrastructure (DEPRECATED)
- RAGService: High-level RAG query service with citation tracking (DEPRECATED)
- Integration with existing embedding_service.py for 768-dim embeddings
- Semantic caching for reduced LLM API calls
"""

import warnings

# Emit deprecation warning when module is imported
warnings.warn(
    "RAGService is deprecated. Use MultimodalSearchService instead.",
    DeprecationWarning,
    stacklevel=2,
)

from typing import Any, Dict, List, Optional, Sequence, Tuple
import uuid

from app.utils.logger import logger


class PGVectorStore:
    """DEPRECATED: Custom PGVector store for RAG operations.

    ⚠️ Use MultimodalSearchService for all queries.
    This class will be removed in v2.0.

    Wraps the existing PGVector infrastructure to provide a unified interface
    for similarity search over paper chunks. Works with or without PaperQA2.

    Attributes:
        connection: Database connection (asyncpg Connection)
        table_name: Name of the chunks table (default: paper_chunks)
        dimension: Embedding dimension (default: 768)
    """

    def __init__(
        self,
        connection: Any,
        table_name: str = "paper_chunks",
        dimension: int = 768,
    ):
        """Initialize PGVectorStore.

        Args:
            connection: asyncpg database connection
            table_name: PostgreSQL table name for chunks
            dimension: Embedding vector dimension
        """
        logger.warning(
            "PGVectorStore.__init__ is DEPRECATED. "
            "Use MultimodalSearchService instead."
        )
        self.connection = connection
        self.table_name = table_name
        self.dimension = dimension

    async def search(
        self,
        query: str,
        paper_ids: List[str],
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Search for similar chunks in PGVector.

        Performs cosine similarity search over the paper_chunks table
        filtered by the specified paper IDs.

        Args:
            query: Search query text
            paper_ids: List of paper UUIDs to search within
            limit: Maximum number of results to return

        Returns:
            List of chunk dictionaries with content, metadata, and similarity scores
        """
        # Generate query embedding using the embedding service
        from app.core.embedding_service import EmbeddingService

        embedding_service = EmbeddingService()
        query_embedding = embedding_service.generate_embedding(query)
        embedding_str = f"[{','.join(str(x) for x in query_embedding)}]"

        # Query database using PGVector cosine distance operator
        rows = await self.connection.fetch(
            f"""SELECT id, paper_id, content, section, page_start, page_end,
                      embedding <=> $1::vector as distance
               FROM {self.table_name}
               WHERE paper_id = ANY($2)
               ORDER BY embedding <=> $1::vector
               LIMIT $3""",
            embedding_str,
            paper_ids,
            limit,
        )

        results = []
        for row in rows:
            # Convert distance to similarity (1 - distance for cosine)
            distance = row["distance"]
            similarity = 1.0 - distance

            results.append({
                "id": row["id"],
                "paper_id": row["paper_id"],
                "content": row["content"],
                "section": row["section"],
                "page": row["page_start"],
                "page_start": row["page_start"],
                "page_end": row["page_end"],
                "similarity": round(similarity, 4),
                "distance": round(distance, 4),
            })

        logger.info(
            "PGVector search completed",
            query=query[:50],
            paper_count=len(paper_ids),
            results_found=len(results),
        )

        return results

    async def add_chunks(
        self,
        chunks: List[Dict[str, Any]],
    ) -> List[str]:
        """Add chunks to the store (placeholder for PaperQA2 compatibility).

        In the current architecture, chunks are added via embedding_service.py.
        This method exists for interface compatibility.

        Args:
            chunks: List of chunk dictionaries to add

        Returns:
            List of chunk IDs
        """
        # Chunks are already stored via embedding_service
        # Return IDs for compatibility
        return [c.get("id", str(uuid.uuid4())) for c in chunks]

    async def delete_by_paper(self, paper_id: str) -> int:
        """Delete all chunks for a paper.

        Args:
            paper_id: Paper UUID

        Returns:
            Number of chunks deleted
        """
        result = await self.connection.execute(
            f"DELETE FROM {self.table_name} WHERE paper_id = $1",
            paper_id,
        )
        # Parse result like "DELETE 5"
        parts = result.split()
        if len(parts) >= 2 and parts[0] == "DELETE":
            return int(parts[1])
        return 0

    def clear(self) -> None:
        """Clear local cache (no-op for database-backed store)."""
        pass


class RAGService:
    """DEPRECATED: RAG query service with citation-aware answering.

    ⚠️ Use MultimodalSearchService for all queries.
    This class will be removed in v2.0.

    Migration:
        OLD: RAGService().query(question, paper_ids, connection=conn)
        NEW: MultimodalSearchService().search(query, paper_ids, user_id)

    Provides high-level RAG capabilities for answering questions based on
    paper content with proper citation tracking and source attribution.

    Attributes:
        pg_store: PGVectorStore instance for similarity search
        embedding_service: EmbeddingService for query embedding
        semantic_cache: SemanticCache for reducing redundant LLM calls
    """

    def __init__(
        self,
        pg_store: Optional[PGVectorStore] = None,
        embedding_service: Optional[Any] = None,
    ):
        """Initialize RAGService.

        Args:
            pg_store: Optional PGVectorStore instance
            embedding_service: Optional EmbeddingService instance
        """
        logger.warning(
            "RAGService.__init__ is DEPRECATED. "
            "Use MultimodalSearchService instead."
        )
        self.pg_store = pg_store
        self._embedding_service = embedding_service
        # Initialize semantic cache with user decision D-02 settings
        from app.core.semantic_cache import SemanticCache
        self.semantic_cache = SemanticCache(threshold=0.95, ttl=86400)

    @property
    def embedding_service(self) -> Any:
        """Lazy load embedding service."""
        if self._embedding_service is None:
            from app.core.embedding_service import EmbeddingService
            self._embedding_service = EmbeddingService()
        return self._embedding_service

    async def query(
        self,
        question: str,
        paper_ids: List[str],
        top_k: int = 5,
        connection: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Execute RAG query with citations and semantic caching.

        ⚠️ DEPRECATED: Use MultimodalSearchService.search() instead.
        This method will be removed in v2.0.

        Migration:
            OLD: RAGService().query(question, paper_ids, top_k=5)
            NEW: MultimodalSearchService().search(query, paper_ids, user_id, top_k=5)

        Retrieves relevant chunks and generates an answer with proper citations.
        This is a simplified implementation that returns retrieved contexts.
        Full PaperQA2 integration can be added later.

        Args:
            question: User question
            paper_ids: List of paper UUIDs to search
            top_k: Number of chunks to retrieve
            connection: Database connection (required if pg_store not set)

        Returns:
            Dictionary with answer, citations, and confidence score
        """
        logger.warning(
            "RAGService.query is DEPRECATED. "
            "Use MultimodalSearchService.search instead."
        )
        if self.pg_store is None and connection is None:
            raise ValueError("Either pg_store or connection must be provided")

        # Check semantic cache first
        cached = await self.semantic_cache.get(question, paper_ids)
        if cached:
            logger.info(
                "Semantic cache hit - returning cached response",
                question=question[:50],
            )
            cached["cached"] = True
            return cached

        store = self.pg_store or PGVectorStore(connection)

        # Retrieve relevant chunks
        chunks = await store.search(
            query=question,
            paper_ids=paper_ids,
            limit=top_k,
        )

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
            citations.append({
                "text": chunk["content"][:500],  # Preview
                "paper_id": chunk["paper_id"],
                "chunk_id": chunk["id"],
                "content_preview": chunk["content"][:500],
                "page": chunk["page"],
                "similarity": chunk["similarity"],
            })

        # Calculate confidence as average similarity of top results
        avg_similarity = sum(c["similarity"] for c in citations) / len(citations)
        confidence = min(avg_similarity * 1.2, 1.0)  # Scale up slightly, cap at 1.0

        # Build context-aware answer (simplified)
        # Full implementation would use LLM to generate answer from contexts
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
        top_k: int = 5,
        connection: Optional[Any] = None,
    ) -> Any:
        """Execute streaming RAG query.

        Generator that yields tokens for SSE streaming response.
        Full implementation would integrate with LiteLLM for token streaming.

        Args:
            question: User question
            paper_ids: List of paper UUIDs to search
            top_k: Number of chunks to retrieve
            connection: Database connection

        Yields:
            Token strings for streaming
        """
        # First retrieve contexts
        result = await self.query(
            question=question,
            paper_ids=paper_ids,
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
            yield f"- Paper {citation['paper_id'][:8]}..., Page {citation['page']}, Score {citation['similarity']:.2f}\n"


# Convenience function for direct usage
async def rag_query(
    question: str,
    paper_ids: List[str],
    connection: Any,
    top_k: int = 5,
) -> Dict[str, Any]:
    """Execute RAG query with minimal setup.

    Args:
        question: User question
        paper_ids: List of paper UUIDs to search
        connection: Database connection
        top_k: Number of chunks to retrieve

    Returns:
        RAG response with answer and citations
    """
    service = RAGService()
    return await service.query(
        question=question,
        paper_ids=paper_ids,
        top_k=top_k,
        connection=connection,
    )
