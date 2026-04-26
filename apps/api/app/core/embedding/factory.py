"""EmbeddingServiceFactory for dynamic embedding service instantiation.

Provides:
- Configuration-driven model selection (EMBEDDING_MODEL)
- Singleton caching per model configuration
- Support for BGE-M3 and Qwen3-VL-Embedding
- Backward compatible get_embedding_service() function

Design decisions (per D-11, D-13):
- Factory pattern for dynamic instantiation
- Configuration via environment variables
- Caching for memory efficiency
- Default to Qwen3-VL for multimodal support

Usage:
    from app.core.embedding.factory import get_embedding_service
    
    # Get embedding service (configured via EMBEDDING_MODEL env var)
    embedding = get_embedding_service()
    embedding.load_model()
    
    # Encode content
    text_embedding = embedding.encode_text("search query")
    image_embedding = embedding.encode_image("image.png")
    table_embedding = embedding.encode_table(caption="Data", headers=[], rows=[])
"""

from typing import Dict
from app.core.embedding.base import BaseEmbeddingService
from app.core.embedding.tongyi_flash_embedding import TongyiFlashEmbeddingService
from app.core.embedding.qwen3vl_embedding import Qwen3VLEmbeddingService
from app.config import settings, normalize_embedding_model_name
from app.core.rag_runtime_profile import (
    OFFICIAL_EMBEDDING_MODEL,
    OFFICIAL_RUNTIME_PROFILE,
)
from app.utils.logger import logger


class EmbeddingServiceFactory:
    """Factory for creating embedding service instances.
    
    Features:
    - Configuration-driven model selection
    - Singleton caching per configuration
    - Support for BGE-M3 and Qwen3-VL-Embedding
    - Default to Qwen3-VL for multimodal support
    
    Configuration:
        EMBEDDING_MODEL: Model type ("bge-m3" or "qwen3-vl-2b")
        EMBEDDING_QUANTIZATION: Quantization type ("int4" or "fp16")
        EMBEDDING_DIMENSION: Embedding dimension (1024 or 2048)
    """

    _instances: Dict[str, BaseEmbeddingService] = {}

    @classmethod
    def create(cls) -> BaseEmbeddingService:
        """Create or retrieve cached embedding service instance.
        
        Uses EMBEDDING_MODEL and EMBEDDING_QUANTIZATION from configuration.
        Caches instances by model type, device, and quantization.
        
        Returns:
            Embedding service instance (BGEEmbeddingService or Qwen3VLEmbeddingService)
            
        Raises:
            ValueError: If EMBEDDING_MODEL is unknown
        """
        # Get configuration (with defaults for backward compatibility)
        model_type = normalize_embedding_model_name(
            getattr(settings, "EMBEDDING_MODEL", "qwen3-vl-2b")
        )
        quantization = getattr(settings, "EMBEDDING_QUANTIZATION", "int4")
        device = "auto"  # Auto-detect device

        # Create cache key
        cache_key = f"{model_type}:{device}:{quantization}"

        # Return cached instance if exists
        if cache_key in cls._instances:
            logger.debug(
                "Returning cached embedding service",
                model_type=model_type,
                cache_key=cache_key,
            )
            return cls._instances[cache_key]

        # Create new instance based on model type
        logger.info(
            "Creating new embedding service",
            model_type=model_type,
            device=device,
            quantization=quantization,
        )

        if (
            getattr(settings, "RAG_RUNTIME_PROFILE", "") == OFFICIAL_RUNTIME_PROFILE
            and model_type != OFFICIAL_EMBEDDING_MODEL
        ):
            raise ValueError(
                "Deprecated embedding model is not allowed in "
                "api_flash_qwen_rerank_glm runtime"
            )

        if model_type == OFFICIAL_EMBEDDING_MODEL:
            service = TongyiFlashEmbeddingService()
        elif model_type == "bge-m3":
            from app.core.embedding.bge_embedding import BGEEmbeddingService
            service = BGEEmbeddingService()
        elif model_type == "qwen3-vl-2b":
            service = Qwen3VLEmbeddingService(
                device=device,
                quantization=quantization
            )
        else:
            raise ValueError(
                f"Unknown embedding model: {model_type}. "
                f"Supported models: {OFFICIAL_EMBEDDING_MODEL}, bge-m3, qwen3-vl-2b"
            )

        # Cache instance
        cls._instances[cache_key] = service

        logger.info(
            "Embedding service created and cached",
            model_type=model_type,
            cache_key=cache_key,
        )

        return service

    @classmethod
    def clear_cache(cls):
        """Clear all cached instances.
        
        Useful for testing or when switching models dynamically.
        """
        cls._instances.clear()
        logger.info("Embedding service cache cleared")


# Backward compatible function (preserves old API)
def get_embedding_service() -> BaseEmbeddingService:
    """Get or create embedding service instance.
    
    Backward compatible function that uses factory internally.
    Returns singleton instance based on EMBEDDING_MODEL configuration.
    
    Returns:
        Embedding service instance
    """
    return EmbeddingServiceFactory.create()


async def create_embedding_service() -> BaseEmbeddingService:
    """Create and initialize embedding service.
    
    Backward compatible async function.
    
    Returns:
        Initialized embedding service instance
    """
    service = get_embedding_service()
    service.load_model()
    return service