"""Object pool for managing reusable model instances.

Avoids repeated model loading overhead by maintaining a pool
of pre-initialized embedding service instances.

Per D-11: Object pool manages Embedding models to avoid repeated loading.
"""

import asyncio
from typing import Optional, TypeVar, Generic, Any

from app.utils.logger import logger


T = TypeVar('T')


class ObjectPool(Generic[T]):
    """Generic object pool for reusable resources.
    
    Maintains a pool of pre-initialized objects that can be
    acquired and released, avoiding repeated initialization overhead.
    """
    
    def __init__(self, pool_size: int = 2):
        """Initialize object pool.
        
        Args:
            pool_size: Maximum number of objects in pool
        """
        self._pool: asyncio.Queue = asyncio.Queue(maxsize=pool_size)
        self._pool_size = pool_size
        self._initialized = False
        self._factory: Optional[callable] = None
    
    def set_factory(self, factory: callable) -> None:
        """Set factory function for creating objects.
        
        Args:
            factory: Async function that creates a new object
        """
        self._factory = factory
    
    async def initialize(self) -> None:
        """Pre-populate pool with objects."""
        if self._initialized or not self._factory:
            return
        
        for i in range(self._pool_size):
            obj = await self._factory()
            await self._pool.put(obj)
            logger.debug(f"Object pool: created object {i+1}/{self._pool_size}")
        
        self._initialized = True
        logger.info(f"Object pool initialized with {self._pool_size} objects")
    
    async def acquire(self) -> T:
        """Acquire an object from the pool.
        
        Returns:
            Object instance from pool
        """
        if not self._initialized:
            await self.initialize()
        
        obj = await self._pool.get()
        logger.debug("Object pool: object acquired")
        return obj
    
    async def release(self, obj: T) -> None:
        """Release an object back to the pool.
        
        Args:
            obj: Object to return to pool
        """
        await self._pool.put(obj)
        logger.debug("Object pool: object released")
    
    @property
    def available(self) -> int:
        """Number of available objects in pool."""
        return self._pool.qsize()


class EmbeddingObjectPool:
    """Specialized pool for Qwen3VL embedding service.
    
    Per D-11: Manages embedding model instances to avoid repeated loading.
    """
    
    def __init__(self, pool_size: int = 2):
        """Initialize embedding object pool.
        
        Args:
            pool_size: Number of model instances to maintain
        """
        self._pool = ObjectPool(pool_size)
        self._initialized = False
        self._service: Any = None
    
    async def initialize(self) -> None:
        """Initialize the embedding object pool."""
        async def create_service():
            from app.core.qwen3vl_service import Qwen3VLMultimodalEmbedding
            from app.core.config import settings
            
            service = Qwen3VLMultimodalEmbedding(
                quantization=settings.EMBEDDING_QUANTIZATION,
                device=settings.EMBEDDING_DEVICE
            )
            service.load_model()
            return service
        
        self._pool.set_factory(create_service)
        await self._pool.initialize()
        self._initialized = True
    
    async def acquire(self):
        """Acquire an embedding service instance."""
        if not self._initialized:
            await self.initialize()
        return await self._pool.acquire()
    
    async def release(self, service) -> None:
        """Release an embedding service back to pool."""
        await self._pool.release(service)
    
    async def __aenter__(self):
        """Context manager entry."""
        self._service = await self.acquire()
        return self._service
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.release(self._service)


# Singleton instance
_embedding_pool: Optional[EmbeddingObjectPool] = None


async def get_embedding_pool() -> EmbeddingObjectPool:
    """Get or create the embedding object pool singleton."""
    global _embedding_pool
    if _embedding_pool is None:
        _embedding_pool = EmbeddingObjectPool(pool_size=2)
    return _embedding_pool