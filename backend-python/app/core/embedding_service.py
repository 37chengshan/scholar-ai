"""Embedding service for generating and storing vector embeddings.

Provides:
- BGE-M3 based embedding generation (1024-dim)
- Batch processing for efficiency
- Milvus vector storage
- Contextual embedding generation using GLM-4.5-Air (Phase 12)
"""

import hashlib
import math
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from app.core.bge_m3_service import get_bge_m3_service
from app.core.milvus_service import get_milvus_service
from app.utils.logger import logger


class EmbeddingService:
    """Service for generating embeddings and storing chunks in Milvus.

    Uses BGE-M3 for 1024-dimensional embeddings.
    """

    EMBEDDING_DIM = 1024  # BGE-M3

    def __init__(self, mock_mode: bool = False):
        """
        Initialize embedding service.

        Args:
            mock_mode: If True, use mock embeddings instead of loading model.
                       Useful for testing without model files.
        """
        self.bge_m3 = get_bge_m3_service()
        self.milvus = get_milvus_service()
        self._dimension = 1024  # BGE-M3
        self._mock_mode = mock_mode or False

    @property
    def dimension(self) -> int:
        """Return the embedding dimension (1024 for BGE-M3)."""
        return 1024  # BGE-M3 fixed dimension

    def _generate_mock_embedding(self, text: str) -> List[float]:
        """Generate deterministic mock embedding for testing (1024-dim)."""
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
        Generate 1024-dim embedding using BGE-M3.

        Args:
            text: Input text to embed

        Returns:
            List of float values representing the 1024-dim embedding vector
        """
        if not text or not text.strip():
            # Return zero vector for empty text
            return [0.0] * self._dimension

        if self._mock_mode:
            return self._generate_mock_embedding(text)

        return self.bge_m3.encode_text(text)

    def generate_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = 32
    ) -> List[List[float]]:
        """
        Generate 1024-dim embeddings using BGE-M3.

        Args:
            texts: List of input texts
            batch_size: Number of texts to process at once (not used, for API compatibility)

        Returns:
            List of 1024-dim embedding vectors
        """
        if not texts:
            return []

        if self._mock_mode:
            return [self._generate_mock_embedding(t) for t in texts]

        return self.bge_m3.encode_text(texts)

    async def store_chunks(
        self,
        paper_id: str,
        user_id: str,
        chunks: List[Dict[str, Any]],
        whole_document: Optional[str] = None
    ) -> List[str]:
        """
        Store chunks with embeddings in Milvus.

        Args:
            paper_id: Paper UUID
            user_id: User UUID for Milvus filtering
            chunks: List of chunk dicts with text, section, page info
            whole_document: Optional full document text for contextual embeddings (Phase 12)

        Returns:
            List of generated chunk IDs (as strings)
        """
        if not chunks:
            return []

        # Generate embeddings - contextual or batch (per Phase 12 Gap 1)
        embeddings_data = []
        
        if whole_document and whole_document.strip():
            # Contextual embedding per chunk (per Phase 12 D-01)
            logger.info(
                "Using contextual embeddings for chunks",
                paper_id=paper_id,
                chunk_count=len(chunks)
            )
            for i, chunk in enumerate(chunks):
                chunk_text = chunk.get("text", "")
                try:
                    embedding, contextualized_text = self.create_contextual_embedding(
                        chunk_text, whole_document
                    )
                    embeddings_data.append({
                        "paper_id": paper_id,
                        "user_id": user_id,
                        "content_type": "text",
                        "page_num": chunk.get("page_start", 0),
                        "section": chunk.get("section", ""),
                        "content_data": contextualized_text[:8000],
                        "embedding": embedding,
                        "text": chunk_text,
                    })
                    logger.debug(
                        "Generated contextual embedding",
                        paper_id=paper_id,
                        chunk_index=i,
                        original_length=len(chunk_text),
                        contextualized_length=len(contextualized_text)
                    )
                except Exception as e:
                    # Fallback to basic embedding if contextual fails
                    logger.warning(
                        "Contextual embedding failed, using fallback",
                        paper_id=paper_id,
                        chunk_index=i,
                        error=str(e)
                    )
                    embedding = self.generate_embedding(chunk_text)
                    embeddings_data.append({
                        "paper_id": paper_id,
                        "user_id": user_id,
                        "content_type": "text",
                        "page_num": chunk.get("page_start", 0),
                        "section": chunk.get("section", ""),
                        "content_data": chunk_text[:8000],
                        "embedding": embedding,
                        "text": chunk_text,
                    })
        else:
            # Fallback to basic batch embedding
            texts = [c.get("text", "") for c in chunks]
            logger.info(
                "Using batch embeddings for chunks (no whole_document)",
                paper_id=paper_id,
                chunk_count=len(chunks)
            )
            embeddings = self.generate_embeddings_batch(texts)
            
            for chunk, embedding in zip(chunks, embeddings):
                chunk_text = chunk.get("text", "")
                embeddings_data.append({
                    "paper_id": paper_id,
                    "user_id": user_id,
                    "content_type": "text",
                    "page_num": chunk.get("page_start", 0),
                    "section": chunk.get("section", ""),
                    "content_data": chunk_text[:8000],
                    "embedding": embedding,
                    "text": chunk_text,
                })

        # Insert to Milvus
        ids = self.milvus.insert_contents(embeddings_data)
        
        logger.info(
            "Stored chunks in Milvus",
            paper_id=paper_id,
            chunk_count=len(ids)
        )

        return [str(id) for id in ids]

    def create_contextual_embedding(
        self,
        chunk_text: str,
        whole_document: str
    ) -> Tuple[List[float], str]:
        """Generate contextual embedding using GLM-4.5-Air per Phase 12 D-01.

        Uses Anthropic's official prompt template to generate context
        that situates the chunk within the whole document.

        Args:
            chunk_text: The chunk to contextualize
            whole_document: Full document text for context

        Returns:
            Tuple of (embedding, contextualized_text)

        Raises:
            Exception: If GLM API fails after retries
        """
        from zhipuai import ZhipuAI
        from app.core.config import settings

        # Anthropic official prompt template (per Phase 12 D-01)
        prompt = f"""<document>
{whole_document}
</document>
Here is the chunk we want to situate within the whole document
<chunk>
{chunk_text}
</chunk>
Please give a short succinct context to situate this chunk within the overall document for the purposes of improving search retrieval of the chunk. Answer only with the succinct context and nothing else."""

        # Initialize ZhipuAI client
        client = ZhipuAI(api_key=settings.ZHIPU_API_KEY)

        # Retry logic with exponential backoff
        max_retries = 5
        base_delay = 1

        for attempt in range(max_retries):
            try:
                # Generate context with GLM-4.5-Air (per Phase 12 D-01)
                response = client.chat.completions.create(
                    model="glm-4.5-air",
                    messages=[{"role": "user", "content": prompt}],
                    thinking={"type": "disabled"},
                    max_tokens=100,
                    temperature=0.3
                )

                context = response.choices[0].message.content

                # Combine context and chunk (per Phase 12 D-01)
                contextualized_text = f"{context}\n\n{chunk_text}"

                # Generate embedding using BGE-M3
                embedding = self.generate_embedding(contextualized_text)

                return embedding, contextualized_text

            except Exception as e:
                logger.warning(
                    "GLM API call failed, retrying",
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    error=str(e)
                )

                if attempt < max_retries - 1:
                    # Exponential backoff
                    delay = base_delay * (2 ** attempt)
                    time.sleep(delay)
                else:
                    # All retries exhausted
                    logger.error(
                        "GLM API failed after all retries",
                        error=str(e)
                    )
                    raise


# Convenience functions for direct usage
def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for texts without instantiating service.

    Args:
        texts: List of input texts

    Returns:
        List of 1024-dim embedding vectors
    """
    service = EmbeddingService()
    return service.generate_embeddings_batch(texts)


async def store_chunks(
    paper_id: str,
    user_id: str,
    chunks: List[Dict[str, Any]],
) -> List[str]:
    """
    Store chunks with embeddings in Milvus.

    Args:
        paper_id: Paper UUID
        user_id: User UUID
        chunks: List of chunk dictionaries

    Returns:
        List of chunk IDs
    """
    service = EmbeddingService()
    return await service.store_chunks(paper_id, user_id, chunks)