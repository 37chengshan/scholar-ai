"""Embedding service for generating and storing vector embeddings.

Provides:
- Sentence-transformer based embedding generation
- Batch processing for efficiency
- PostgreSQL PGVector storage with asyncpg
- Similarity search using pgvector operators
"""

import hashlib
import math
import os
import uuid
from typing import Any, Dict, List, Optional

import numpy as np

from app.utils.logger import logger


class EmbeddingService:
    """Service for generating embeddings and storing chunks in PGVector."""

    # Model configurations with their dimensions
    MODEL_CONFIGS = {
        "sentence-transformers/all-MiniLM-L6-v2": {"dims": 384, "normalize": True},
        "sentence-transformers/all-mpnet-base-v2": {"dims": 768, "normalize": True},
        "sentence-transformers/all-distilroberta-v1": {"dims": 768, "normalize": True},
    }

    def __init__(self, model_name: Optional[str] = None, mock_mode: bool = False):
        """
        Initialize embedding service.

        Args:
            model_name: HuggingFace model name. Defaults to all-mpnet-base-v2
                       for 768 dimensions matching test expectations.
            mock_mode: If True, use mock embeddings instead of loading model.
                      Useful for testing without network access.
        """
        self.model_name = model_name or os.getenv(
            "EMBEDDING_MODEL",
            "sentence-transformers/all-mpnet-base-v2"  # 768 dims for test compatibility
        )
        self._model = None
        self._mock_mode = mock_mode or os.getenv("EMBEDDING_MOCK_MODE", "").lower() == "true"
        self._dimension = self._get_expected_dimension()

    def _get_expected_dimension(self) -> int:
        """Get expected embedding dimension for configured model."""
        if self.model_name in self.MODEL_CONFIGS:
            return self.MODEL_CONFIGS[self.model_name]["dims"]
        # Default to 768 for unknown models
        return 768

    @property
    def model(self):
        """Lazy load the embedding model."""
        if self._model is None and not self._mock_mode:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info("Loading embedding model", model=self.model_name)
                self._model = SentenceTransformer(self.model_name)
                # Verify actual dimension
                self._dimension = self._model.get_sentence_embedding_dimension()
                logger.info(
                    "Embedding model loaded",
                    model=self.model_name,
                    dimension=self._dimension
                )
            except Exception as e:
                logger.warning(
                    "Failed to load embedding model, using mock mode",
                    error=str(e)
                )
                self._mock_mode = True
        return self._model

    @property
    def dimension(self) -> int:
        """Return the embedding dimension."""
        if self._model is not None and not self._mock_mode:
            return self._model.get_sentence_embedding_dimension()
        return self._dimension

    def _generate_mock_embedding(self, text: str) -> List[float]:
        """Generate deterministic mock embedding for testing."""
        # Use text hash as seed for deterministic embeddings
        hash_val = hashlib.md5(text.encode()).hexdigest()

        # Generate pseudo-random vector based on hash
        vector = []
        seed = int(hash_val[:8], 16)

        # Simple pseudo-random number generator
        def next_rand():
            nonlocal seed
            seed = (seed * 1103515245 + 12345) & 0x7fffffff
            return (seed / 0x7fffffff) * 2 - 1

        for _ in range(self._dimension):
            vector.append(next_rand())

        # Normalize to unit length (L2 norm = 1)
        magnitude = math.sqrt(sum(x * x for x in vector))
        if magnitude > 0:
            vector = [x / magnitude for x in vector]

        return vector

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Input text to embed

        Returns:
            List of float values representing the embedding vector
        """
        if not text or not text.strip():
            # Return zero vector for empty text
            return [0.0] * self.dimension

        if self._mock_mode:
            return self._generate_mock_embedding(text)

        embedding = self.model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
        return embedding.tolist()

    def generate_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = 32
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts efficiently.

        Args:
            texts: List of input texts
            batch_size: Number of texts to process at once

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        if self._mock_mode:
            return [self._generate_mock_embedding(t) for t in texts]

        # Filter out empty texts
        valid_texts = [t if t and t.strip() else "" for t in texts]

        embeddings = self.model.encode(
            valid_texts,
            convert_to_numpy=True,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=False
        )

        return [e.tolist() for e in embeddings]

    async def store_chunks(
        self,
        conn: Any,  # asyncpg.Connection
        paper_id: str,
        chunks: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Store chunks with embeddings in PostgreSQL.

        Args:
            conn: Database connection (asyncpg)
            paper_id: Paper UUID
            chunks: List of chunk dicts with text, section, page info

        Returns:
            List of generated chunk IDs
        """
        if not chunks:
            return []

        chunk_ids = []
        texts = [c.get("text", "") for c in chunks]

        # Generate embeddings in batch
        logger.info(
            "Generating embeddings for chunks",
            paper_id=paper_id,
            chunk_count=len(chunks)
        )
        embeddings = self.generate_embeddings_batch(texts)

        for chunk, embedding in zip(chunks, embeddings):
            chunk_id = str(uuid.uuid4())

            # Extract metadata
            section = chunk.get("section")
            page_start = chunk.get("page_start")
            page_end = chunk.get("page_end", page_start)
            media = chunk.get("media", [])

            # Determine media flags
            is_table = any(m.get("type") == "table" for m in media)
            is_figure = any(m.get("type") == "picture" for m in media)
            is_formula = any(m.get("type") == "formula" for m in media)

            # Limit content size
            content = chunk.get("text", "")[:8000]

            # Convert embedding to PostgreSQL vector format
            embedding_str = f"[{','.join(str(x) for x in embedding)}]"

            await conn.execute(
                """INSERT INTO paper_chunks (
                    id, \"paperId\", content, section, page_start, page_end,
                    embedding, is_table, is_figure, is_formula
                ) VALUES ($1, $2, $3, $4, $5, $6, $7::vector, $8, $9, $10)""",
                chunk_id,
                paper_id,
                content,
                section,
                page_start,
                page_end,
                embedding_str,
                is_table,
                is_figure,
                is_formula
            )

            chunk_ids.append(chunk_id)

        logger.info(
            "Stored chunks in PostgreSQL",
            paper_id=paper_id,
            chunk_count=len(chunk_ids)
        )

        return chunk_ids

    async def search_similar(
        self,
        conn: Any,  # asyncpg.Connection
        query: str,
        paper_ids: Optional[List[str]] = None,
        limit: int = 10,
        section: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar chunks by vector similarity.

        Uses PGVector <=> operator for cosine distance.

        Args:
            conn: Database connection
            query: Search query text
            paper_ids: Optional list of paper IDs to search within
            limit: Maximum number of results
            section: Optional section filter

        Returns:
            List of matching chunks with similarity scores
        """
        query_embedding = self.generate_embedding(query)
        embedding_str = f"[{','.join(str(x) for x in query_embedding)}]"

        # Build query based on filters
        if paper_ids and section:
            # Filter by both paper IDs and section
            rows = await conn.fetch(
                """SELECT id, paper_id, content, section, page_start, page_end,
                          embedding <=> $1::vector as distance
                   FROM paper_chunks
                   WHERE paper_id = ANY($2) AND section = $3
                   ORDER BY embedding <=> $1::vector
                   LIMIT $4""",
                embedding_str,
                paper_ids,
                section,
                limit
            )
        elif paper_ids:
            # Filter by paper IDs only
            rows = await conn.fetch(
                """SELECT id, paper_id, content, section, page_start, page_end,
                          embedding <=> $1::vector as distance
                   FROM paper_chunks
                   WHERE paper_id = ANY($2)
                   ORDER BY embedding <=> $1::vector
                   LIMIT $3""",
                embedding_str,
                paper_ids,
                limit
            )
        elif section:
            # Filter by section only
            rows = await conn.fetch(
                """SELECT id, paper_id, content, section, page_start, page_end,
                          embedding <=> $1::vector as distance
                   FROM paper_chunks
                   WHERE section = $2
                   ORDER BY embedding <=> $1::vector
                   LIMIT $3""",
                embedding_str,
                section,
                limit
            )
        else:
            # No filters
            rows = await conn.fetch(
                """SELECT id, paper_id, content, section, page_start, page_end,
                          embedding <=> $1::vector as distance
                   FROM paper_chunks
                   ORDER BY embedding <=> $1::vector
                   LIMIT $2""",
                embedding_str,
                limit
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
                "similarity": round(similarity, 4),
                "distance": round(distance, 4),
            })

        return results

    async def delete_chunks_by_paper(
        self,
        conn: Any,  # asyncpg.Connection
        paper_id: str
    ) -> int:
        """
        Delete all chunks for a paper.

        Args:
            conn: Database connection
            paper_id: Paper UUID

        Returns:
            Number of chunks deleted
        """
        result = await conn.execute(
            "DELETE FROM paper_chunks WHERE paper_id = $1",
            paper_id
        )
        # Parse result like "DELETE 5"
        parts = result.split()
        if len(parts) >= 2 and parts[0] == "DELETE":
            return int(parts[1])
        return 0

    async def update_chunk_embedding(
        self,
        conn: Any,  # asyncpg.Connection
        chunk_id: str,
        new_text: str
    ) -> bool:
        """
        Update a chunk's embedding after text change.

        Args:
            conn: Database connection
            chunk_id: Chunk UUID
            new_text: New text content

        Returns:
            True if updated, False if chunk not found
        """
        new_embedding = self.generate_embedding(new_text)
        embedding_str = f"[{','.join(str(x) for x in new_embedding)}]"

        result = await conn.execute(
            """UPDATE paper_chunks
               SET content = $1, embedding = $2::vector
               WHERE id = $3""",
            new_text[:8000],
            embedding_str,
            chunk_id
        )

        # Parse result like "UPDATE 1"
        parts = result.split()
        if len(parts) >= 2 and parts[0] == "UPDATE":
            return int(parts[1]) > 0
        return False


# Convenience functions for direct usage
def generate_embeddings(texts: List[str], model_name: Optional[str] = None) -> List[List[float]]:
    """
    Generate embeddings for texts without instantiating service.

    Args:
        texts: List of input texts
        model_name: Optional model name override

    Returns:
        List of embedding vectors
    """
    service = EmbeddingService(model_name=model_name)
    return service.generate_embeddings_batch(texts)


async def store_chunks(
    conn: Any,
    paper_id: str,
    chunks: List[Dict[str, Any]],
    model_name: Optional[str] = None
) -> List[str]:
    """
    Store chunks with embeddings.

    Args:
        conn: Database connection
        paper_id: Paper UUID
        chunks: List of chunk dictionaries
        model_name: Optional model name override

    Returns:
        List of chunk IDs
    """
    service = EmbeddingService(model_name=model_name)
    return await service.store_chunks(conn, paper_id, chunks)
