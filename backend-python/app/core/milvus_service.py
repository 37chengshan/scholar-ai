"""Milvus service for vector database operations.

Provides:
- Connection pooling with retry logic
- Collection creation for paper_images and paper_tables
- Vector insertion, search, and deletion
- Index management (IVF_FLAT with Cosine similarity)
- Proper connection lifecycle management
"""

import time
from typing import List, Dict, Any, Optional
from functools import wraps

from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType
from pymilvus.exceptions import MilvusException

from app.core.config import settings
from app.utils.logger import logger


def retry_with_backoff(max_retries: int = 5, base_delay: float = 1.0):
    """Decorator for retry with exponential backoff."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except MilvusException as e:
                    if attempt == max_retries - 1:
                        raise
                    delay = base_delay * (2 ** attempt)
                    logger.warning(
                        "Milvus operation failed, retrying",
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        delay=delay,
                        error=str(e)
                    )
                    time.sleep(delay)
            return None
        return wrapper
    return decorator


class MilvusService:
    """Milvus connection wrapper with connection pooling."""

    EMBEDDING_DIM = 768

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        pool_size: int = 10,
        timeout: int = 10
    ):
        self.host = host or settings.MILVUS_HOST
        self.port = port or settings.MILVUS_PORT
        self.pool_size = pool_size
        self.timeout = timeout
        self._alias = "scholarai"
        self._connected = False

    @retry_with_backoff(max_retries=5)
    def connect(self) -> None:
        """Establish connection with connection pooling."""
        if self._connected:
            return

        try:
            connections.connect(
                alias=self._alias,
                host=self.host,
                port=self.port,
                pool_size=self.pool_size,
                timeout=self.timeout
            )
            self._connected = True
            logger.info(
                "Milvus connected",
                host=self.host,
                port=self.port,
                pool_size=self.pool_size
            )
        except Exception as e:
            logger.error("Failed to connect to Milvus", error=str(e))
            raise

    def disconnect(self) -> None:
        """Close all connections."""
        if self._connected:
            try:
                connections.disconnect(self._alias)
                logger.info("Milvus disconnected")
            except Exception as e:
                logger.warning("Error disconnecting from Milvus", error=str(e))
            finally:
                self._connected = False

    def is_connected(self) -> bool:
        """Check if connection is active."""
        return self._connected

    def _create_collection_schema(self, name: str, fields: List[FieldSchema]) -> Collection:
        """Create collection with schema."""
        schema = CollectionSchema(fields, f"ScholarAI {name} collection")
        collection = Collection(name, schema, using=self._alias)
        return collection

    def _create_index(self, collection: Collection, field_name: str = "embedding") -> None:
        """Create IVF_FLAT index for vector field."""
        index_params = {
            "metric_type": "COSINE",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 128}
        }
        collection.create_index(field_name, index_params)
        logger.info(
            "Created index",
            collection=collection.name,
            field=field_name,
            index_type="IVF_FLAT"
        )

    def create_paper_images_collection(self) -> Collection:
        """Create paper_images collection with proper schema."""
        fields = [
            FieldSchema(
                name="id",
                dtype=DataType.INT64,
                is_primary=True,
                auto_id=True,
                description="Auto-increment ID"
            ),
            FieldSchema(
                name="paper_id",
                dtype=DataType.VARCHAR,
                max_length=64,
                description="Paper UUID"
            ),
            FieldSchema(
                name="user_id",
                dtype=DataType.VARCHAR,
                max_length=64,
                description="User ID for filtering"
            ),
            FieldSchema(
                name="page_num",
                dtype=DataType.INT32,
                description="Page number"
            ),
            FieldSchema(
                name="caption",
                dtype=DataType.VARCHAR,
                max_length=1024,
                description="Image caption"
            ),
            FieldSchema(
                name="image_type",
                dtype=DataType.VARCHAR,
                max_length=32,
                description="Image type: figure/chart/diagram"
            ),
            FieldSchema(
                name="embedding",
                dtype=DataType.FLOAT_VECTOR,
                dim=self.EMBEDDING_DIM,
                description="768-dim embedding"
            ),
            FieldSchema(
                name="bbox",
                dtype=DataType.JSON,
                description="Bounding box coordinates"
            ),
        ]

        collection = self._create_collection_schema("paper_images", fields)
        self._create_index(collection, "embedding")
        collection.load()

        logger.info(
            "Created paper_images collection",
            embedding_dim=self.EMBEDDING_DIM
        )
        return collection

    def create_paper_tables_collection(self) -> Collection:
        """Create paper_tables collection with proper schema."""
        fields = [
            FieldSchema(
                name="id",
                dtype=DataType.INT64,
                is_primary=True,
                auto_id=True,
                description="Auto-increment ID"
            ),
            FieldSchema(
                name="paper_id",
                dtype=DataType.VARCHAR,
                max_length=64,
                description="Paper UUID"
            ),
            FieldSchema(
                name="user_id",
                dtype=DataType.VARCHAR,
                max_length=64,
                description="User ID for filtering"
            ),
            FieldSchema(
                name="page_num",
                dtype=DataType.INT32,
                description="Page number"
            ),
            FieldSchema(
                name="table_data",
                dtype=DataType.JSON,
                description="Structured table data"
            ),
            FieldSchema(
                name="description",
                dtype=DataType.VARCHAR,
                max_length=1024,
                description="Table description"
            ),
            FieldSchema(
                name="embedding",
                dtype=DataType.FLOAT_VECTOR,
                dim=self.EMBEDDING_DIM,
                description="768-dim embedding"
            ),
        ]

        collection = self._create_collection_schema("paper_tables", fields)
        self._create_index(collection, "embedding")
        collection.load()

        logger.info(
            "Created paper_tables collection",
            embedding_dim=self.EMBEDDING_DIM
        )
        return collection

    def create_collections(self) -> Dict[str, Collection]:
        """Create all collections."""
        self.connect()

        collections = {}

        # Create paper_images collection if not exists
        try:
            collections["paper_images"] = Collection(
                settings.MILVUS_COLLECTION_IMAGES,
                using=self._alias
            )
            logger.info("paper_images collection already exists")
        except MilvusException:
            collections["paper_images"] = self.create_paper_images_collection()

        # Create paper_tables collection if not exists
        try:
            collections["paper_tables"] = Collection(
                settings.MILVUS_COLLECTION_TABLES,
                using=self._alias
            )
            logger.info("paper_tables collection already exists")
        except MilvusException:
            collections["paper_tables"] = self.create_paper_tables_collection()

        return collections

    def get_collection(self, name: str) -> Collection:
        """Get collection by name."""
        return Collection(name, using=self._alias)

    def search_images(
        self,
        embedding: List[float],
        user_id: Optional[str] = None,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """Search for similar images."""
        collection = self.get_collection(settings.MILVUS_COLLECTION_IMAGES)

        search_params = {
            "metric_type": "COSINE",
            "params": {"nprobe": 10}
        }

        # Build expression for user filtering
        expr = f"user_id == '{user_id}'" if user_id else None

        results = collection.search(
            data=[embedding],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            expr=expr,
            output_fields=["paper_id", "page_num", "caption", "image_type", "bbox"]
        )

        # Format results
        formatted = []
        for hits in results:
            for hit in hits:
                formatted.append({
                    "id": hit.id,
                    "distance": hit.distance,
                    "paper_id": hit.entity.get("paper_id"),
                    "page_num": hit.entity.get("page_num"),
                    "caption": hit.entity.get("caption"),
                    "image_type": hit.entity.get("image_type"),
                    "bbox": hit.entity.get("bbox"),
                })
        return formatted

    def search_tables(
        self,
        embedding: List[float],
        user_id: Optional[str] = None,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """Search for similar tables."""
        collection = self.get_collection(settings.MILVUS_COLLECTION_TABLES)

        search_params = {
            "metric_type": "COSINE",
            "params": {"nprobe": 10}
        }

        # Build expression for user filtering
        expr = f"user_id == '{user_id}'" if user_id else None

        results = collection.search(
            data=[embedding],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            expr=expr,
            output_fields=["paper_id", "page_num", "table_data", "description"]
        )

        # Format results
        formatted = []
        for hits in results:
            for hit in hits:
                formatted.append({
                    "id": hit.id,
                    "distance": hit.distance,
                    "paper_id": hit.entity.get("paper_id"),
                    "page_num": hit.entity.get("page_num"),
                    "table_data": hit.entity.get("table_data"),
                    "description": hit.entity.get("description"),
                })
        return formatted

    def insert_images(self, data: List[Dict[str, Any]]) -> List[int]:
        """Insert image embeddings."""
        collection = self.get_collection(settings.MILVUS_COLLECTION_IMAGES)

        # Prepare data
        entities = []
        for item in data:
            entities.append({
                "paper_id": item["paper_id"],
                "user_id": item["user_id"],
                "page_num": item["page_num"],
                "caption": item.get("caption", ""),
                "image_type": item.get("image_type", "figure"),
                "embedding": item["embedding"],
                "bbox": item.get("bbox", {}),
            })

        ids = collection.insert(entities)
        collection.flush()
        logger.info(f"Inserted {len(entities)} images")
        return ids.primary_keys

    def insert_tables(self, data: List[Dict[str, Any]]) -> List[int]:
        """Insert table embeddings."""
        collection = self.get_collection(settings.MILVUS_COLLECTION_TABLES)

        # Prepare data
        entities = []
        for item in data:
            entities.append({
                "paper_id": item["paper_id"],
                "user_id": item["user_id"],
                "page_num": item["page_num"],
                "table_data": item.get("table_data", {}),
                "description": item.get("description", ""),
                "embedding": item["embedding"],
            })

        ids = collection.insert(entities)
        collection.flush()
        logger.info(f"Inserted {len(entities)} tables")
        return ids.primary_keys

    def delete_by_paper(self, paper_id: str) -> None:
        """Delete all vectors for a paper."""
        # Delete from images collection
        img_collection = self.get_collection(settings.MILVUS_COLLECTION_IMAGES)
        img_collection.delete(f'paper_id == "{paper_id}"')
        img_collection.flush()

        # Delete from tables collection
        tbl_collection = self.get_collection(settings.MILVUS_COLLECTION_TABLES)
        tbl_collection.delete(f'paper_id == "{paper_id}"')
        tbl_collection.flush()

        logger.info(f"Deleted vectors for paper {paper_id}")


# Singleton instance
_milvus_service: Optional[MilvusService] = None


def get_milvus_service() -> MilvusService:
    """Get or create MilvusService singleton."""
    global _milvus_service
    if _milvus_service is None:
        _milvus_service = MilvusService()
    return _milvus_service
