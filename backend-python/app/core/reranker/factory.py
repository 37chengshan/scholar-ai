"""RerankerServiceFactory for dynamic reranker instantiation.

Provides:
- Configuration-driven model selection (RERANKER_MODEL)
- Singleton caching per model configuration
- Support for BGE-Reranker and Qwen3-VL-Reranker
- Backward compatible get_reranker_service() function

Design decisions (per D-R02):
- Factory pattern for dynamic instantiation
- Configuration via environment variables
- Caching for memory efficiency
- Default to BGE-Reranker for backward compatibility

Usage:
    from app.core.reranker.factory import get_reranker_service
    
    # Get reranker (configured via RERANKER_MODEL env var)
    reranker = get_reranker_service()
    reranker.load_model()
    
    # Rerank documents
    results = reranker.rerank(query, documents, top_k=10)
"""

from typing import Dict, Any
from app.core.reranker.base import BaseRerankerService
from app.core.reranker.bge_reranker import BGERerankerService
from app.core.reranker.qwen3vl_reranker import Qwen3VLRerankerService
from app.config import settings
from app.utils.logger import logger


class RerankerServiceFactory:
    """Factory for creating reranker service instances.
    
    Features:
    - Configuration-driven model selection
    - Singleton caching per configuration
    - Support for BGE-Reranker and Qwen3-VL-Reranker
    - Default to BGE-Reranker for backward compatibility
    
    Configuration:
        RERANKER_MODEL: Model type ("bge-reranker" or "qwen3-vl-reranker")
        RERANKER_QUANTIZATION: Quantization type ("fp16" or "int8")
    """

    _instances: Dict[str, BaseRerankerService] = {}

    @classmethod
    def create(cls) -> BaseRerankerService:
        """Create or retrieve cached reranker service instance.
        
        Uses RERANKER_MODEL and RERANKER_QUANTIZATION from configuration.
        Caches instances by model type, device, and quantization.
        
        Returns:
            Reranker service instance (BGERerankerService or Qwen3VLRerankerService)
            
        Raises:
            ValueError: If RERANKER_MODEL is unknown
        """
        # Get configuration (with defaults for backward compatibility)
        model_type = getattr(settings, "RERANKER_MODEL", "bge-reranker")
        quantization = getattr(settings, "RERANKER_QUANTIZATION", "fp16")
        device = "auto"  # Auto-detect device

        # Create cache key
        cache_key = f"{model_type}:{device}:{quantization}"

        # Return cached instance if exists
        if cache_key in cls._instances:
            logger.debug(
                "Returning cached reranker service",
                model_type=model_type,
                cache_key=cache_key,
            )
            return cls._instances[cache_key]

        # Create new instance based on model type
        logger.info(
            "Creating new reranker service",
            model_type=model_type,
            device=device,
            quantization=quantization,
        )

        if model_type == "bge-reranker":
            service = BGERerankerService()
        elif model_type == "qwen3-vl-reranker":
            service = Qwen3VLRerankerService(
                device=device,
                quantization=quantization
            )
        else:
            raise ValueError(
                f"Unknown reranker model: {model_type}. "
                f"Supported models: bge-reranker, qwen3-vl-reranker"
            )

        # Cache instance
        cls._instances[cache_key] = service

        logger.info(
            "Reranker service created and cached",
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
        logger.info("Reranker service cache cleared")


# Backward compatible function (preserves old API)
def get_reranker_service() -> BaseRerankerService:
    """Get or create reranker service instance.
    
    Backward compatible function that uses factory internally.
    Returns singleton instance based on RERANKER_MODEL configuration.
    
    Returns:
        Reranker service instance
    """
    return RerankerServiceFactory.create()


async def create_reranker_service() -> BaseRerankerService:
    """Create and initialize reranker service.
    
    Backward compatible async function.
    
    Returns:
        Initialized reranker service instance
    """
    service = get_reranker_service()
    service.load_model()
    return service