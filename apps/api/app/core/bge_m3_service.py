"""BGE-M3 unified embedding service for multimodal content.

Provides:
- Text encoding to 1024-dim vectors
- Table encoding via serialization to text
- Singleton pattern for model efficiency
- FP16 optimization for memory efficiency

BGE-M3 is used as the unified embedding model for all content types
to enable cross-modal retrieval in a single vector space.
"""

import json
from typing import Any, Dict, List, Optional, Union

from FlagEmbedding import BGEM3FlagModel

from app.utils.logger import logger


class BGEM3Service:
    """BGE-M3 unified embedding service.

    Features:
    - 1024-dimensional dense embeddings
    - 8192 token maximum sequence length
    - FP16 mode for memory efficiency
    - Batch encoding support
    - Table serialization to text format
    """

    MODEL_NAME = "BAAI/bge-m3"
    EMBEDDING_DIM = 1024
    MAX_SEQ_LENGTH = 8192

    def __init__(self):
        self.model: Optional[BGEM3FlagModel] = None
        self.device = "cuda" if self._check_cuda() else "cpu"
        self._initialized = False

    def _check_cuda(self) -> bool:
        """Check if CUDA is available."""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False

    def load_model(self) -> None:
        """Load model into memory. Called at app startup."""
        if self._initialized:
            return

        try:
            logger.info(
                "Loading BGE-M3 model",
                model=self.MODEL_NAME,
                device=self.device,
            )

            import os
            from pathlib import Path
            
            cache_dir = Path.home() / ".cache" / "huggingface" / "hub" / "models--BAAI--bge-m3"
            snapshot_file = cache_dir / "refs" / "main"
            
            if snapshot_file.exists():
                snapshot_hash = snapshot_file.read_text().strip()
                local_path = cache_dir / "snapshots" / snapshot_hash
                if local_path.exists():
                    logger.info("Using cached BGE-M3 model", path=str(local_path))
                    model_path = str(local_path)
                else:
                    model_path = self.MODEL_NAME
            else:
                model_path = self.MODEL_NAME

            use_fp16 = self.device == "cuda"
            self.model = BGEM3FlagModel(
                model_path,
                use_fp16=use_fp16,
                devices=self.device,
            )
            self._initialized = True

            logger.info(
                "BGE-M3 model loaded successfully",
                embedding_dim=self.EMBEDDING_DIM,
                device=self.device,
                use_fp16=use_fp16,
            )
        except Exception as e:
            logger.error("Failed to load BGE-M3 model", error=str(e))
            raise

    def encode_text(
        self,
        texts: Union[str, List[str]]
    ) -> Union[List[float], List[List[float]]]:
        """Encode text(s) to 1024-dim vectors.

        Args:
            texts: Single text string or list of strings

        Returns:
            Single 1024-dim vector for single input,
            or list of vectors for batch input
        """
        if not self._initialized:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        # Handle single string input
        is_single = isinstance(texts, str)
        if is_single:
            texts = [texts]

        # Handle empty inputs
        if not texts:
            if is_single:
                return [0.0] * self.EMBEDDING_DIM
            return []

        # Normalize all values to strings before tokenization.
        # Dataset extraction may occasionally surface non-string values.
        processed_texts: List[str] = []
        empty_indices: set[int] = set()
        for i, text in enumerate(texts):
            normalized_text = self._normalize_text_value(text)
            if not normalized_text.strip():
                processed_texts.append("")  # Will be handled below
                empty_indices.add(i)
            else:
                processed_texts.append(normalized_text)

        # Encode non-empty texts - filter out empty strings
        non_empty_texts = [t for t in processed_texts if t.strip()]

        if non_empty_texts:
            embeddings_result = self.model.encode(
                non_empty_texts,
                batch_size=32,
                max_length=self.MAX_SEQ_LENGTH,
            )["dense_vecs"]

            # Convert to list format
            embeddings_list = embeddings_result.tolist()

            # Merge back empty positions with zero vectors
            embeddings = []
            non_empty_idx = 0
            for i in range(len(processed_texts)):
                if i in empty_indices:
                    embeddings.append([0.0] * self.EMBEDDING_DIM)
                else:
                    embeddings.append(embeddings_list[non_empty_idx])
                    non_empty_idx += 1
        else:
            # All texts were empty
            embeddings = [[0.0] * self.EMBEDDING_DIM for _ in processed_texts]

        # Return single vector for single input, list for batch
        if is_single:
            return embeddings[0] if embeddings else [0.0] * self.EMBEDDING_DIM
        return embeddings

    def _normalize_text_value(self, value: Any) -> str:
        """Normalize unknown input values into tokenizer-safe text."""
        if value is None:
            return ""
        if isinstance(value, str):
            normalized = value
        elif isinstance(value, bytes):
            normalized = value.decode("utf-8", errors="ignore")
        elif isinstance(value, (dict, list, tuple, set)):
            normalized = json.dumps(value, ensure_ascii=False, default=str)
        else:
            normalized = str(value)

        # Drop invalid unicode code points that may appear in extracted PDF text.
        return normalized.encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")

    def encode_table(
        self,
        caption: str = "",
        description: str = "",
        headers: Optional[List[str]] = None,
        sample_rows: Optional[List[Dict]] = None,
    ) -> List[float]:
        """Encode table to 1024-dim vector.

        Serializes table structure to text and encodes it.

        Args:
            caption: Table caption/title
            description: Table description
            headers: Column headers
            sample_rows: Sample rows as list of dicts

        Returns:
            1024-dimensional embedding vector
        """
        serialized = self._serialize_table(caption, description, headers, sample_rows)
        return self.encode_text(serialized)

    def _serialize_table(
        self,
        caption: str = "",
        description: str = "",
        headers: Optional[List[str]] = None,
        sample_rows: Optional[List[Dict]] = None,
    ) -> str:
        """Serialize table to text format.

        Format:
            Table: {caption}
            Description: {description}
            Columns: {header1}, {header2}, ...
            Sample data: {row1_data}, {row2_data}, ...

        Args:
            caption: Table caption
            description: Table description
            headers: Column headers
            sample_rows: Sample rows (max 3 rows)

        Returns:
            Serialized table text
        """
        parts = []

        if caption:
            parts.append(f"Table: {caption}")

        if description:
            parts.append(f"Description: {description}")

        if headers:
            parts.append(f"Columns: {', '.join(headers)}")

        if sample_rows:
            # Truncate to max 3 rows
            rows = sample_rows[:3]
            row_texts = []
            for row in rows:
                row_str = ", ".join(f"{k}={v}" for k, v in row.items())
                row_texts.append(row_str)
            parts.append(f"Sample data: {'; '.join(row_texts)}")

        return "\n".join(parts)

    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._initialized

    def get_device(self) -> str:
        """Get the device being used (cuda/cpu)."""
        return self.device

    def get_embedding_dim(self) -> int:
        """Get the embedding dimension."""
        return self.EMBEDDING_DIM


# Singleton instance
_bge_m3_service: Optional[BGEM3Service] = None


def get_bge_m3_service() -> BGEM3Service:
    """Get or create BGEM3Service singleton."""
    global _bge_m3_service
    if _bge_m3_service is None:
        _bge_m3_service = BGEM3Service()
    return _bge_m3_service


async def create_bge_m3_service() -> BGEM3Service:
    """Create and initialize BGEM3Service.

    Returns:
        Initialized BGEM3Service instance
    """
    service = get_bge_m3_service()
    service.load_model()
    return service
