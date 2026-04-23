"""SPECTER 2 Embedding Service - Scientific paper specialized embeddings.

SPECTER2 (Scientific Paper Embeddings for Classification, Regression, Retrieval, and Recommendation)
is developed by Allen Institute for AI and specifically trained on 6M+ scientific paper citations.

Key Features:
- Trained on citation graphs (papers cite similar papers)
- Task-specific adapters for different use cases
- Optimized for English scientific papers
- Base model: SciBERT (110M) + Adapters
- Output: 768 dimensions
- Max context: 512 tokens

Adapters available:
- proximity: Paper-to-paper similarity (default)
- adhoc_query: Short query to paper search
- classification: Paper classification tasks
- regression: Paper regression tasks

Paper: https://arxiv.org/abs/2301.11342
Model: https://huggingface.co/allenai/specter2
License: Apache 2.0
"""

import os
import re
from typing import Any, Dict, List, Literal, Optional

import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer

from app.utils.logger import logger

# Try to import adapters, provide fallback if not available
try:
    from adapters import AutoAdapterModel
    ADAPTERS_AVAILABLE = True
except ImportError:
    ADAPTERS_AVAILABLE = False
    logger.warning("adapters library not installed. SPECTER2 will fall back to base model.")


class Specter2EmbeddingService:
    """SPECTER 2 embedding service specialized for scientific papers.

    Recommended for:
    - English academic papers
    - Paper recommendation systems
    - Citation prediction
    - Paper classification/regression

    Not recommended for:
    - Non-English papers (limited support)
    - Long documents (>512 tokens)
    - General domain text

    Hardware requirements:
    - GPU: Optional, ~2GB VRAM
    - RAM: ~4GB
    - Storage: ~500MB for model + adapters
    """

    BASE_MODEL = "allenai/specter2_base"
    ADAPTERS = {
        "proximity": "allenai/specter2",  # Paper-to-paper similarity
        "adhoc_query": "allenai/specter2_adhoc_query",  # Query to paper
        "classification": "allenai/specter2_classification",  # Classification
        "regression": "allenai/specter2_regression",  # Regression
    }
    DIMENSION = 768
    MAX_TOKENS = 512

    def __init__(
        self,
        adapter: Literal["proximity", "adhoc_query", "classification", "regression"] = "proximity",
        device: Optional[str] = None,
    ):
        """Initialize SPECTER 2 embedding service.

        Args:
            adapter: Task-specific adapter to use
                - proximity: For paper-to-paper similarity (default, best for retrieval)
                - adhoc_query: For short query search
                - classification: For classification tasks
                - regression: For regression tasks
            device: 'cuda', 'cpu', or None for auto
        """
        self.adapter_name = adapter
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self._adapters_enabled = ADAPTERS_AVAILABLE

        self._tokenizer: Optional[Any] = None
        self._model: Optional[Any] = None

        logger.info(
            "Initializing SPECTER 2 service",
            base_model=self.BASE_MODEL,
            adapter=adapter,
            device=self.device,
        )

    def _load_model(self):
        """Lazy load model, tokenizer, and adapter."""
        if self._model is None:
            local_root = os.getenv("SPECTER2_MODEL_DIR", "").strip()
            local_base = os.path.join(local_root, "specter2_base") if local_root else ""
            adapter_dir_map = {
                "proximity": "specter2_proximity_adapter",
                "adhoc_query": "specter2_adhoc_query_adapter",
            }
            local_adapter = ""
            if local_root and self.adapter_name in adapter_dir_map:
                local_adapter = os.path.join(local_root, adapter_dir_map[self.adapter_name])

            base_ref = local_base if local_base and os.path.isdir(local_base) else self.BASE_MODEL

            logger.info("Loading SPECTER 2 model...", base_model=base_ref)

            # Load tokenizer
            self._tokenizer = AutoTokenizer.from_pretrained(base_ref)

            if self._adapters_enabled:
                # Load base model with adapter support
                self._model = AutoAdapterModel.from_pretrained(base_ref)

                # Load and activate adapter
                adapter_path = self.ADAPTERS.get(
                    self.adapter_name,
                    self.ADAPTERS["proximity"],
                )
                if local_adapter and os.path.isdir(local_adapter):
                    adapter_path = local_adapter
                self._model.load_adapter(
                    adapter_path,
                    source="hf" if adapter_path.startswith("allenai/") else "local",
                    set_active=True,
                )
            else:
                # Fallback path for environments where adapters cannot be installed
                self._model = AutoModel.from_pretrained(base_ref)

            self._model.to(self.device)
            self._model.eval()

            logger.info(
                "SPECTER 2 model loaded",
                device=self.device,
                adapter=self.adapter_name,
                adapters_enabled=self._adapters_enabled,
                parameters=sum(p.numel() for p in self._model.parameters()),
            )

    @property
    def dimension(self) -> int:
        """Return embedding dimension."""
        return self.DIMENSION

    def _truncate_text(self, text: str) -> str:
        """Truncate text to max token limit."""
        # Rough estimation: 1 token ≈ 4 characters
        max_chars = self.MAX_TOKENS * 3
        if len(text) > max_chars:
            return text[:max_chars]
        return text

    def _preprocess_paper(self, text: str) -> str:
        """Preprocess paper text for SPECTER 2.

        SPECTER 2 expects: [CLS] Title [SEP] Abstract [SEP]
        If input doesn't have clear title/abstract separation,
        we try to extract or format it.
        """
        # If text looks like title + abstract already, use as is
        if len(text) < self.MAX_TOKENS * 3:
            return text

        # Try to extract title and abstract
        lines = text.strip().split('\n')

        # First non-empty line is likely title
        title = ""
        abstract = ""

        for line in lines:
            line = line.strip()
            if line and not title:
                title = line
            elif line and not abstract:
                # Look for abstract marker
                if line.lower().startswith('abstract'):
                    abstract = line[8:].strip()
                elif len(line) > 50:  # Likely abstract
                    abstract = line
            elif abstract:
                abstract += " " + line

            if len(title) + len(abstract) > self.MAX_TOKENS * 3:
                break

        if title and abstract:
            return f"{title} [SEP] {abstract}"

        # Fallback: truncate
        return self._truncate_text(text)

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for scientific paper text.

        Args:
            text: Paper text (title + abstract recommended)

        Returns:
            768-dimension embedding vector
        """
        self._load_model()

        if not text or not text.strip():
            return [0.0] * self.dimension

        # Preprocess for SPECTER 2
        processed_text = self._preprocess_paper(text)

        # Tokenize
        inputs = self._tokenizer(
            processed_text,
            padding=True,
            truncation=True,
            max_length=self.MAX_TOKENS,
            return_tensors="pt",
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        # Generate embedding
        with torch.no_grad():
            outputs = self._model(**inputs)
            # Use [CLS] token representation
            embedding = outputs.last_hidden_state[:, 0]
            # Normalize
            embedding = torch.nn.functional.normalize(embedding, p=2, dim=1)

        return embedding[0].cpu().float().tolist()

    def generate_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = 8,
    ) -> List[List[float]]:
        """Generate embeddings for multiple papers.

        Args:
            texts: List of paper texts
            batch_size: Batch size (default 8, SPECTER is smaller so can be larger)

        Returns:
            List of 768-dimension embedding vectors
        """
        self._load_model()

        if not texts:
            return []

        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch = [self._preprocess_paper(t) if t else "" for t in batch]

            # Tokenize
            inputs = self._tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=self.MAX_TOKENS,
                return_tensors="pt",
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # Generate embeddings
            with torch.no_grad():
                outputs = self._model(**inputs)
                embeddings = outputs.last_hidden_state[:, 0]
                embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)

            all_embeddings.extend(embeddings.cpu().float().tolist())

        return all_embeddings


class SmartEmbeddingService:
    """Smart embedding service that auto-selects best model for the input.

    Selection logic:
    1. English paper + short (<512 tokens) → SPECTER 2 (best for academic)
    2. Non-English or long (>512 tokens) → BGE-M3 (multilingual + long context)
    3. Can override with explicit backend parameter
    """

    # Language detection patterns
    NON_ENGLISH_PATTERNS = [
        r'[\u4e00-\u9fff]',  # Chinese
        r'[\u3040-\u309f\u30a0-\u30ff]',  # Japanese
        r'[\uac00-\ud7af]',  # Korean
        r'[\u0400-\u04ff]',  # Cyrillic (Russian, etc.)
        r'[\u0600-\u06ff]',  # Arabic
        r'[\u0370-\u03ff]',  # Greek
    ]

    def __init__(
        self,
        backend: Optional[str] = None,  # "auto", "bge-m3", "specter2", or None for env
        specter_adapter: str = "proximity",
    ):
        """Initialize smart embedding service.

        Args:
            backend: Override backend selection
                - "auto": Auto-select based on content (default)
                - "bge-m3": Force BGE-M3
                - "specter2": Force SPECTER 2
            specter_adapter: SPECTER 2 adapter to use
        """
        self.backend_override = backend or os.getenv("EMBEDDING_BACKEND", "auto")
        self.specter_adapter = specter_adapter

        self._bge_service: Optional[Any] = None
        self._specter_service: Optional[Any] = None

    def _detect_language(self, text: str) -> str:
        """Detect if text is primarily non-English."""
        for pattern in self.NON_ENGLISH_PATTERNS:
            if re.search(pattern, text):
                return "non-english"
        return "english"

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation."""
        return len(text) // 4

    def select_backend(self, text: str) -> str:
        """Select best backend for the text.

        Returns:
            "bge-m3" or "specter2"
        """
        if self.backend_override in ["bge-m3", "bge_m3"]:
            return "bge-m3"
        elif self.backend_override == "specter2":
            return "specter2"

        # Auto selection logic
        language = self._detect_language(text)
        tokens = self._estimate_tokens(text)

        # Decision tree
        if language == "non-english":
            logger.debug("Auto-selected BGE-M3 (non-English)")
            return "bge-m3"

        if tokens > 512:
            logger.debug("Auto-selected BGE-M3 (long document)")
            return "bge-m3"

        # English + short = SPECTER 2 for best academic performance
        logger.debug("Auto-selected SPECTER 2 (English academic)")
        return "specter2"

    @property
    def bge_service(self) -> Any:
        """Lazy load BGE-M3 service."""
        if self._bge_service is None:
            from app.core.bge_embedding_service import BGEM3EmbeddingService
            self._bge_service = BGEM3EmbeddingService()
        return self._bge_service

    @property
    def specter_service(self) -> Any:
        """Lazy load SPECTER 2 service."""
        if self._specter_service is None:
            self._specter_service = Specter2EmbeddingService(
                adapter=self.specter_adapter
            )
        return self._specter_service

    @property
    def dimension(self) -> int:
        """Return dimension (may vary by backend)."""
        # Default to BGE-M3 dimension if auto
        if self.backend_override == "auto":
            return 1024  # BGE-M3
        elif self.backend_override in ["bge-m3", "bge_m3"]:
            return 1024
        else:
            return 768  # SPECTER 2

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding with auto-selected backend."""
        backend = self.select_backend(text)

        if backend == "bge-m3":
            return self.bge_service.generate_embedding(text)
        else:
            return self.specter_service.generate_embedding(text)

    def generate_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = 8,
    ) -> List[List[float]]:
        """Generate embeddings with backend selection per text.

        Note: If texts have mixed languages, may use different backends.
        For efficiency, uses majority backend for batch.
        """
        if not texts:
            return []

        # Select backend based on first text (assumes batch is similar)
        backend = self.select_backend(texts[0])

        if backend == "bge-m3":
            return self.bge_service.generate_embeddings_batch(texts, batch_size)
        else:
            return self.specter_service.generate_embeddings_batch(texts, batch_size)

    def get_backend_info(self, text: str) -> Dict[str, Any]:
        """Get backend selection info for a text.

        Returns:
            Dict with selected backend and reason
        """
        backend = self.select_backend(text)
        language = self._detect_language(text)
        tokens = self._estimate_tokens(text)

        reason = f"Language: {language}, Tokens: ~{tokens}"
        if backend == "bge-m3":
            if language == "non-english":
                recommendation = "Use BGE-M3 for non-English papers"
            else:
                recommendation = "Use BGE-M3 for long documents (>512 tokens)"
        else:
            recommendation = "Use SPECTER 2 for English academic papers (best quality)"

        return {
            "backend": backend,
            "language": language,
            "estimated_tokens": tokens,
            "reason": reason,
            "recommendation": recommendation,
        }


# Convenience functions
def create_embedding_service(
    backend: Optional[str] = None,
    **kwargs
) -> Any:
    """Factory function to create appropriate embedding service.

    Args:
        backend: "auto", "bge-m3", "specter2", "sentence-transformers"
        **kwargs: Additional arguments for specific services

    Returns:
        Embedding service instance
    """
    backend = backend or os.getenv("EMBEDDING_BACKEND", "auto")

    if backend == "auto":
        return SmartEmbeddingService(**kwargs)
    elif backend in ["bge-m3", "bge_m3"]:
        from app.core.bge_embedding_service import BGEM3EmbeddingService
        return BGEM3EmbeddingService(**kwargs)
    elif backend == "specter2":
        return Specter2EmbeddingService(**kwargs)
    elif backend == "sentence-transformers":
        from app.core.qwen3vl_service import get_qwen3vl_service
        return get_qwen3vl_service()
    else:
        raise ValueError(f"Unknown backend: {backend}")
