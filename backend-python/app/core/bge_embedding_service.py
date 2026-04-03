"""BGE-M3 Embedding Service - Open source alternative to Voyage AI.

BGE-M3 (Beijing Academy of General Intelligence - Multi-lingual, Multi-granularity, Multi-task)
is an open-source embedding model that rivals commercial APIs like Voyage and OpenAI.

Features:
- 100+ languages support
- 8192 token context (long documents)
- Multi-granularity: sentence, paragraph, document level
- Sparse + Dense hybrid retrieval
- 2.2B parameters, 1024 dimensions
- Completely free and open source (MIT license)

Model: BAAI/bge-m3 on Hugging Face
"""

import os
from typing import Any, Dict, List, Optional

import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer

from app.utils.logger import logger


class BGEM3EmbeddingService:
    """BGE-M3 embedding service - open source academic paper embedding.

    Recommended as free alternative to Voyage AI.

    Model capabilities:
    - Input: Up to 8192 tokens (perfect for long academic papers)
    - Output: 1024 dimension vectors
    - Languages: 100+ including English, Chinese, Japanese, etc.
    - License: MIT (free for commercial use)

    Hardware requirements:
    - GPU: Optional but recommended (CUDA)
    - RAM: ~8GB for model loading
    - Storage: ~9GB for model files
    """

    MODEL_NAME = "BAAI/bge-m3"
    DIMENSION = 1024
    MAX_TOKENS = 8192
    BATCH_SIZE = 8  # Adjust based on GPU memory

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
        use_fp16: bool = True,
    ):
        """Initialize BGE-M3 embedding service.

        Args:
            model_name: HuggingFace model name (default: BAAI/bge-m3)
            device: 'cuda', 'cpu', or None for auto
            use_fp16: Use half precision for faster inference
        """
        self.model_name = model_name or self.MODEL_NAME
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.use_fp16 = use_fp16 and self.device == "cuda"

        self._tokenizer: Optional[Any] = None
        self._model: Optional[Any] = None

        logger.info(
            "Initializing BGE-M3 service",
            model=self.model_name,
            device=self.device,
            fp16=self.use_fp16,
        )

    def _load_model(self):
        """Lazy load model and tokenizer."""
        if self._model is None:
            logger.info("Loading BGE-M3 model...", model=self.model_name)

            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self._model = AutoModel.from_pretrained(self.model_name)
            self._model.to(self.device)
            self._model.eval()

            if self.use_fp16:
                self._model = self._model.half()

            logger.info(
                "BGE-M3 model loaded",
                device=self.device,
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

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for single text.

        Args:
            text: Input text to embed

        Returns:
            1024-dimension embedding vector
        """
        self._load_model()

        if not text or not text.strip():
            return [0.0] * self.dimension

        text = self._truncate_text(text)

        # Tokenize
        inputs = self._tokenizer(
            text,
            padding=True,
            truncation=True,
            max_length=self.MAX_TOKENS,
            return_tensors="pt",
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        # Generate embedding
        with torch.no_grad():
            outputs = self._model(**inputs)
            # Use CLS token representation
            embedding = outputs.last_hidden_state[:, 0]
            # Normalize
            embedding = torch.nn.functional.normalize(embedding, p=2, dim=1)

        return embedding[0].cpu().float().tolist()

    def generate_embeddings_batch(
        self,
        texts: List[str],
        batch_size: Optional[int] = None,
    ) -> List[List[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of input texts
            batch_size: Batch size (default: 8)

        Returns:
            List of 1024-dimension embedding vectors
        """
        self._load_model()

        if not texts:
            return []

        batch_size = batch_size or self.BATCH_SIZE
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            batch = [self._truncate_text(t) if t else "" for t in batch]

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

    def generate_sparse_embedding(self, text: str) -> Dict[str, float]:
        """Generate sparse embedding for hybrid retrieval.

        BGE-M3 supports learned sparse retrieval (similar to BM25 but learned).

        Args:
            text: Input text

        Returns:
            Dictionary of {token_id: weight}
        """
        self._load_model()

        # This requires the model to be in specific mode
        # Implementation depends on BGE-M3's sparse output capability
        # For now, return empty dict as placeholder
        logger.warning("Sparse embedding not yet implemented")
        return {}


class OpenSourceEmbeddingService:
    """Unified open source embedding service supporting multiple models.

    Supports:
    - BGE-M3 (recommended): 1024d, multilingual, long context
    - GTE-large: 1024d, fast inference
    - E5-large: 1024d, instruction-tuned
    """

    MODEL_CONFIGS = {
        # BGE series (智源研究院)
        "BAAI/bge-m3": {"dims": 1024, "max_tokens": 8192, " multilingual": True},
        "BAAI/bge-large-en-v1.5": {"dims": 1024, "max_tokens": 512},
        "BAAI/bge-base-en-v1.5": {"dims": 768, "max_tokens": 512},
        "BAAI/bge-small-en-v1.5": {"dims": 384, "max_tokens": 512},

        # GTE series (阿里巴巴)
        "Alibaba-NLP/gte-large-en-v1.5": {"dims": 1024, "max_tokens": 8192},
        "Alibaba-NLP/gte-base-en-v1.5": {"dims": 768, "max_tokens": 8192},
        "Alibaba-NLP/gte-Qwen2-7B-instruct": {"dims": 3584, "max_tokens": 131072},

        # E5 series (Microsoft)
        "intfloat/e5-large-v2": {"dims": 1024, "max_tokens": 512, "multilingual": True},
        "intfloat/e5-base-v2": {"dims": 768, "max_tokens": 512},
        "intfloat/e5-mistral-7b-instruct": {"dims": 4096, "max_tokens": 32768},

        # SFR series (Salesforce)
        "Salesforce/SFR-Embedding-2_R": {"dims": 4096, "max_tokens": 32768},

        # Current default
        "sentence-transformers/all-mpnet-base-v2": {"dims": 768, "max_tokens": 384},
    }

    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        device: Optional[str] = None,
    ):
        """Initialize open source embedding service.

        Args:
            model_name: HuggingFace model name
            device: 'cuda', 'cpu', or None for auto
        """
        self.model_name = model_name

        if model_name.startswith("BAAI/bge-m3"):
            self._service = BGEM3EmbeddingService(model_name, device)
        elif model_name.startswith("sentence-transformers"):
            # Use existing sentence-transformers service
            from app.core.embedding_service import EmbeddingService
            self._service = EmbeddingService(model_name=model_name)
        else:
            # Generic transformer-based embedding
            self._service = BGEM3EmbeddingService(model_name, device)

    @property
    def dimension(self) -> int:
        """Return embedding dimension."""
        return self.MODEL_CONFIGS.get(self.model_name, {}).get("dims", 1024)

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding."""
        return self._service.generate_embedding(text)

    def generate_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = 8,
    ) -> List[List[float]]:
        """Generate embeddings in batch."""
        if hasattr(self._service, 'generate_embeddings_batch'):
            return self._service.generate_embeddings_batch(texts, batch_size)
        return [self._service.generate_embedding(t) for t in texts]


def recommend_model(
    priority: str = "balanced",
    gpu_available: bool = True,
    multilingual: bool = False,
) -> str:
    """Recommend best open source model based on requirements.

    Args:
        priority: 'quality', 'speed', 'balanced'
        gpu_available: Whether GPU is available
        multilingual: Whether multilingual support needed

    Returns:
        Recommended model name
    """
    if priority == "quality":
        if gpu_available:
            return "BAAI/bge-m3"  # Best quality, requires GPU for speed
        return "BAAI/bge-large-en-v1.5"

    elif priority == "speed":
        return "BAAI/bge-small-en-v1.5"  # Fastest, lower quality

    else:  # balanced
        if multilingual:
            return "BAAI/bge-m3"
        return "Alibaba-NLP/gte-large-en-v1.5"


# Model comparison data
MODEL_COMPARISON = """
## BGE-M3 vs Voyage AI vs OpenAI

| Feature | BGE-M3 | Voyage-3 | OpenAI text-3-large |
|---------|--------|----------|---------------------|
| Cost | FREE | $0.10/1M | $0.13/1M |
| Dimensions | 1024 | 1024 | 3072 |
| Max Tokens | 8192 | 32000 | 8191 |
| Languages | 100+ | 100+ | 100+ |
| MTEB Score | 66.36 | ~68* | 64.59 |
| License | MIT | Commercial | Commercial |
| Self-hosted | ✅ | ❌ | ❌ |

*Voyage doesn't publish MTEB, but benchmarks show superior performance on academic texts
"""
