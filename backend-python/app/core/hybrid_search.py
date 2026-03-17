"""Hybrid Search service with dense (PGVector) + sparse (tsvector) + RRF fusion.

Provides:
- dense_search(): Semantic search using PGVector embeddings
- sparse_search(): Lexical search using PostgreSQL tsvector
- reciprocal_rank_fusion(): RRF fusion with configurable weights
- HybridSearchService: High-level service combining both approaches

The hybrid approach uses:
- Dense weight: 0.6 (semantic similarity prioritization)
- Sparse weight: 0.4 (lexical matching)
- RRF k: 60 (standard academic value)

Requirements:
- SEARCH-01: Semantic search in user's library
- SEARCH-04: Hybrid search with configurable weights
"""

from typing import Any, Dict, List, Optional, Tuple

from app.utils.logger import logger


def reciprocal_rank_fusion(
    dense_results: List[Dict[str, Any]],
    sparse_results: List[Dict[str, Any]],
    dense_weight: float = 0.6,
    sparse_weight: float = 0.4,
    k: int = 60,
) -> List[Dict[str, Any]]:
    """Fuse dense and sparse search results using Reciprocal Rank Fusion.

    RRF formula: score = sum(weight / (k + rank)) for each list containing the item

    Args:
        dense_results: Results from dense vector search, each with 'id' and 'score'
        sparse_results: Results from sparse text search, each with 'id' and 'score'
        dense_weight: Weight for dense results (default 0.6)
        sparse_weight: Weight for sparse results (default 0.4)
        k: RRF constant, typically 60 for academic search

    Returns:
        List of fused results sorted by RRF score descending
    """
    # Map of chunk_id -> fused result
    fused_map: Dict[str, Dict[str, Any]] = {}

    # Process dense results (rank starts at 1)
    for rank, result in enumerate(dense_results, start=1):
        chunk_id = result["id"]
        rrf_score = dense_weight * (1.0 / (k + rank))

        if chunk_id not in fused_map:
            fused_map[chunk_id] = {
                "id": chunk_id,
                "rrf_score": 0.0,
                "dense_rank": rank,
                "sparse_rank": None,
                "dense_score": result.get("score", 0.0),
                "sparse_score": 0.0,
                "paper_id": result.get("paper_id"),
                "content": result.get("content", ""),
                "section": result.get("section"),
                "page": result.get("page"),
            }
        fused_map[chunk_id]["rrf_score"] += rrf_score

    # Process sparse results
    for rank, result in enumerate(sparse_results, start=1):
        chunk_id = result["id"]
        rrf_score = sparse_weight * (1.0 / (k + rank))

        if chunk_id not in fused_map:
            fused_map[chunk_id] = {
                "id": chunk_id,
                "rrf_score": 0.0,
                "dense_rank": None,
                "sparse_rank": rank,
                "dense_score": 0.0,
                "sparse_score": result.get("score", 0.0),
                "paper_id": result.get("paper_id"),
                "content": result.get("content", ""),
                "section": result.get("section"),
                "page": result.get("page"),
            }
        else:
            fused_map[chunk_id]["sparse_rank"] = rank
            fused_map[chunk_id]["sparse_score"] = result.get("score", 0.0)

        fused_map[chunk_id]["rrf_score"] += rrf_score

    # Convert to list and sort by RRF score descending
    fused_results = list(fused_map.values())
    fused_results.sort(key=lambda x: x["rrf_score"], reverse=True)

    return fused_results


async def dense_search(
    connection: Any,
    query: str,
    paper_ids: List[str],
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Perform dense vector search using PGVector.

    Uses cosine similarity over 768-dim embeddings stored in paper_chunks.

    Args:
        connection: asyncpg database connection
        query: Search query text
        paper_ids: List of paper UUIDs to search within
        limit: Maximum number of results to return

    Returns:
        List of results with id, paper_id, content, section, page, score, similarity
    """
    from app.core.embedding_service import EmbeddingService

    # Generate query embedding
    embedding_service = EmbeddingService()
    query_embedding = embedding_service.generate_embedding(query)
    embedding_str = f"[{','.join(str(x) for x in query_embedding)}]"

    # Execute cosine similarity search
    rows = await connection.fetch(
        """SELECT id, paper_id, content, section, page_start, page_end,
                  embedding <=> $1::vector as distance
           FROM paper_chunks
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
            "score": round(similarity, 4),
            "similarity": round(similarity, 4),
            "distance": round(distance, 4),
        })

    logger.info(
        "Dense search completed",
        query=query[:50],
        paper_count=len(paper_ids),
        results_found=len(results),
    )

    return results


async def sparse_search(
    connection: Any,
    query: str,
    paper_ids: List[str],
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Perform sparse text search using PostgreSQL tsvector.

    Uses full-text search with tsvector/tsquery for lexical matching.

    Args:
        connection: asyncpg database connection
        query: Search query text
        paper_ids: List of paper UUIDs to search within
        limit: Maximum number of results to return

    Returns:
        List of results with id, paper_id, content, section, page, score, rank
    """
    # Convert query to tsquery format
    # Replace spaces with & for AND operation, escape special characters
    tsquery = _prepare_tsquery(query)

    rows = await connection.fetch(
        """SELECT id, paper_id, content, section, page_start, page_end,
                  ts_rank_cd(search_vector, to_tsquery('english', $1), 32) as rank
           FROM paper_chunks
           WHERE paper_id = ANY($2)
             AND search_vector @@ to_tsquery('english', $1)
           ORDER BY ts_rank_cd(search_vector, to_tsquery('english', $1), 32) DESC
           LIMIT $3""",
        tsquery,
        paper_ids,
        limit,
    )

    results = []
    for row in rows:
        rank = row["rank"]

        results.append({
            "id": row["id"],
            "paper_id": row["paper_id"],
            "content": row["content"],
            "section": row["section"],
            "page": row["page_start"],
            "page_start": row["page_start"],
            "page_end": row["page_end"],
            "score": round(rank, 4),
            "rank": round(rank, 4),
        })

    logger.info(
        "Sparse search completed",
        query=query[:50],
        paper_count=len(paper_ids),
        results_found=len(results),
    )

    return results


def _prepare_tsquery(query: str) -> str:
    """Prepare query string for PostgreSQL tsquery.

    Converts natural language query to tsquery format:
    - Splits on whitespace
    - Joins with & (AND operator)
    - Escapes special characters

    Args:
        query: Raw search query

    Returns:
        Formatted tsquery string
    """
    # Remove extra whitespace and split into terms
    terms = query.strip().split()

    # Escape special characters in each term
    escaped_terms = []
    for term in terms:
        # Escape single quotes and backslashes
        escaped = term.replace("\\", "\\\\").replace("'", "''")
        # Remove other special tsquery characters
        escaped = ''.join(c for c in escaped if c not in '&|!():*')
        if escaped:
            escaped_terms.append(escaped)

    if not escaped_terms:
        return "''"

    # Join with & (AND operator) for intersection
    return " & ".join(f"'{term}'" for term in escaped_terms)


class HybridSearchService:
    """Hybrid search service combining dense and sparse retrieval.

    Provides unified interface for semantic + lexical search with RRF fusion.

    Attributes:
        connection: Database connection (asyncpg)
        dense_weight: Weight for dense search results (default 0.6)
        sparse_weight: Weight for sparse search results (default 0.4)
        rrf_k: RRF constant (default 60)
    """

    def __init__(
        self,
        connection: Optional[Any] = None,
        dense_weight: float = 0.6,
        sparse_weight: float = 0.4,
        rrf_k: int = 60,
    ):
        """Initialize HybridSearchService.

        Args:
            connection: Optional database connection
            dense_weight: Weight for dense results (0.0-1.0)
            sparse_weight: Weight for sparse results (0.0-1.0)
            rrf_k: RRF constant for fusion
        """
        self.connection = connection
        self.dense_weight = dense_weight
        self.sparse_weight = sparse_weight
        self.rrf_k = rrf_k

    async def search(
        self,
        query: str,
        paper_ids: List[str],
        limit: int = 10,
        use_hybrid: bool = True,
        connection: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        """Execute hybrid search query.

        Performs both dense and sparse search, then fuses results with RRF.
        If use_hybrid is False, only dense search is performed.

        Args:
            query: Search query text
            paper_ids: List of paper UUIDs to search within
            limit: Maximum number of results to return
            use_hybrid: If True, combine dense + sparse; else dense only
            connection: Optional database connection (uses self.connection if not provided)

        Returns:
            List of search results with RRF scores
        """
        conn = connection or self.connection
        if conn is None:
            raise ValueError("Database connection required")

        if not paper_ids:
            return []

        if not use_hybrid:
            # Dense search only
            return await dense_search(conn, query, paper_ids, limit)

        # Fetch more results for fusion to ensure good coverage
        fetch_limit = max(limit * 2, 20)

        # Execute both searches concurrently
        import asyncio

        dense_task = dense_search(conn, query, paper_ids, fetch_limit)
        sparse_task = sparse_search(conn, query, paper_ids, fetch_limit)

        dense_results, sparse_results = await asyncio.gather(
            dense_task, sparse_task, return_exceptions=True
        )

        # Handle exceptions
        if isinstance(dense_results, Exception):
            logger.error("Dense search failed", error=str(dense_results))
            dense_results = []
        if isinstance(sparse_results, Exception):
            logger.error("Sparse search failed", error=str(sparse_results))
            sparse_results = []

        # Fuse results with RRF
        fused = reciprocal_rank_fusion(
            dense_results=dense_results,
            sparse_results=sparse_results,
            dense_weight=self.dense_weight,
            sparse_weight=self.sparse_weight,
            k=self.rrf_k,
        )

        # Return top results
        return fused[:limit]

    async def search_with_details(
        self,
        query: str,
        paper_ids: List[str],
        limit: int = 10,
        connection: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Execute hybrid search with detailed metadata.

        Args:
            query: Search query text
            paper_ids: List of paper UUIDs to search within
            limit: Maximum number of results to return
            connection: Optional database connection

        Returns:
            Dictionary with results and search metadata
        """
        conn = connection or self.connection

        results = await self.search(
            query=query,
            paper_ids=paper_ids,
            limit=limit,
            use_hybrid=True,
            connection=conn,
        )

        return {
            "query": query,
            "paper_count": len(paper_ids),
            "result_count": len(results),
            "weights": {
                "dense": self.dense_weight,
                "sparse": self.sparse_weight,
            },
            "results": results,
        }


# Convenience functions for direct usage

async def hybrid_search(
    query: str,
    paper_ids: List[str],
    connection: Any,
    limit: int = 10,
    dense_weight: float = 0.6,
    sparse_weight: float = 0.4,
) -> List[Dict[str, Any]]:
    """Execute hybrid search with minimal setup.

    Args:
        query: Search query text
        paper_ids: List of paper UUIDs to search within
        connection: Database connection
        limit: Maximum number of results
        dense_weight: Weight for dense results
        sparse_weight: Weight for sparse results

    Returns:
        List of fused search results
    """
    service = HybridSearchService(
        connection=connection,
        dense_weight=dense_weight,
        sparse_weight=sparse_weight,
    )
    return await service.search(query, paper_ids, limit)
