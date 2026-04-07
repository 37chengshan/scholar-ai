"""Milvus service for vector database operations.

Provides:
- Connection pooling with retry logic
- Collection creation for paper_images and paper_tables
- Vector insertion, search, and deletion
- Index management (IVF_FLAT with Cosine similarity)
- Proper connection lifecycle management
- Quality scoring for chunks (per D-06)
"""

import re
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


def is_header_footer(text: str) -> bool:
    """Detect if text is header/footer (per D-06).
    
    Args:
        text: Text to check
        
    Returns:
        True if text matches header/footer patterns
    """
    # Check for common patterns (per D-06 lines 407-427 in CONTEXT.md)
    patterns = [
        r"^\d+\s*$",  # Page numbers
        r"^\d{4}-\d{2}-\d{2}",  # Dates
        r"^(Page|第)\s*\d+",  # Page labels
    ]
    return any(re.match(p, text.strip()) for p in patterns)


def calculate_chunk_quality(chunk: dict) -> float:
    """Calculate chunk quality score per D-06.
    
    Args:
        chunk: Chunk dictionary with text and metadata
        
    Returns:
        Quality score in 0-1 range
    """
    score = 1.0
    text = chunk.get("text", "")
    
    # Reduce low-quality content (per D-06 lines 407-427 in CONTEXT.md)
    if len(text) < 50:
        score *= 0.3  # Too short
    
    if is_header_footer(text):
        score *= 0.2  # Header/footer
    
    if "references" in chunk.get("section", "").lower():
        score *= 0.5  # References section
    
    # Boost high-quality content
    if chunk.get("has_equations") or chunk.get("has_figures"):
        score *= 1.2
    
    return min(score, 1.0)


class MilvusService:
    """Milvus connection wrapper with connection pooling."""
    
    # Per D-27: 50-vector batches for reliability
    MILVUS_BATCH_SIZE = 50
    # Per D-29: Max 3 retries with exponential backoff
    MAX_RETRIES = 3

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
        
        # Use embedding dimension from config (per Phase 18)
        # Supports: Qwen3-VL (2048), BGE-M3 (1024), or other models
        self.embedding_dim = settings.EMBEDDING_DIMENSION

        # Create paper_contents_v2 collection if not exists per D-09
        # This happens on first use, not on instantiation
        # The actual creation happens in create_collections() or create_collection_v2()

    def initialize_collections(self) -> None:
        """Initialize collections on startup.

        Creates paper_contents_v2 collection per D-09.
        Deletes old paper_contents collection per D-08, D-10.
        """
        self.connect()

        # Create paper_contents_v2 collection if not exists per D-09
        if not self.has_collection(settings.MILVUS_COLLECTION_CONTENTS_V2):
            self.create_collection_v2()
            logger.info("Created paper_contents_v2 collection on startup")

        # Delete old paper_contents collection per D-08, D-10
        if self.has_collection(settings.MILVUS_COLLECTION_CONTENTS):  # "paper_contents"
            logger.warning("Deleting old paper_contents collection (1024-dim BGE-M3 data)")
            self.drop_collection(settings.MILVUS_COLLECTION_CONTENTS)
            logger.info("Old paper_contents collection deleted, all BGE-M3 data removed")

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
                dim=self.embedding_dim,
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
            embedding_dim=self.embedding_dim
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
                dim=self.embedding_dim,
                description="768-dim embedding"
            ),
        ]

        collection = self._create_collection_schema("paper_tables", fields)
        self._create_index(collection, "embedding")
        collection.load()

        logger.info(
            "Created paper_tables collection",
            embedding_dim=self.embedding_dim
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

        # Create paper_contents collection (unified 1024-dim) if not exists
        try:
            collections["paper_contents"] = Collection(
                settings.MILVUS_COLLECTION_CONTENTS,
                using=self._alias
            )
            logger.info("paper_contents collection already exists")
        except MilvusException:
            collections["paper_contents"] = self.create_paper_contents_collection()

        return collections

    def get_collection(self, name: str) -> Collection:
        """Get collection by name, ensuring connection is established."""
        if not self._connected:
            self.connect()
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

    def has_collection(self, collection_name: str) -> bool:
        """Check if collection exists.

        Args:
            collection_name: Name of collection to check

        Returns:
            True if collection exists, False otherwise
        """
        try:
            self.connect()
            return connections.has_collection(collection_name, using=self._alias)
        except Exception as e:
            logger.warning(f"Error checking collection existence: {e}")
            return False

    def drop_collection(self, collection_name: str) -> None:
        """Drop a Milvus collection per D-08.

        Args:
            collection_name: Name of collection to drop
        """
        if self.has_collection(collection_name):
            try:
                collection = Collection(collection_name, using=self._alias)
                collection.drop()
                logger.info(f"Dropped collection {collection_name}")
            except Exception as e:
                logger.error(f"Failed to drop collection {collection_name}: {e}")
                raise
        else:
            logger.warning(f"Collection {collection_name} does not exist, skip dropping")

    def create_collection_v2(self) -> None:
        """Create paper_contents_v2 collection with 2048-dim embeddings per D-09."""
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="paper_id", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="user_id", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="page_num", dtype=DataType.INT64),
            FieldSchema(name="content_type", dtype=DataType.VARCHAR, max_length=32),
            FieldSchema(name="section", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="quality_score", dtype=DataType.FLOAT),
            FieldSchema(name="word_count", dtype=DataType.INT64),
            FieldSchema(name="has_equations", dtype=DataType.BOOL),
            FieldSchema(name="has_figures", dtype=DataType.BOOL),
            FieldSchema(name="extraction_version", dtype=DataType.INT64),
            FieldSchema(name="content_data", dtype=DataType.VARCHAR, max_length=8000),
            FieldSchema(name="raw_data", dtype=DataType.JSON),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.embedding_dim),
        ]
        
        schema = CollectionSchema(fields, "Multimodal content with Qwen3-VL embeddings")
        collection = Collection(settings.MILVUS_COLLECTION_CONTENTS_V2, schema, using=self._alias)
        
        index_params = {"metric_type": "COSINE", "index_type": "IVF_FLAT", "params": {"nlist": 100}}
        collection.create_index("embedding", index_params)
        collection.load()
        
        logger.info("Created paper_contents_v2 collection", embedding_dim=self.embedding_dim)

    def create_paper_contents_collection(self) -> Collection:
        """Create unified paper_contents collection with enhanced schema (per D-06).

        This collection stores all multimodal content (images, tables, text)
        with BGE-M3 1024-dimensional embeddings for unified retrieval.
        
        Enhanced with 6 metadata fields for quality scoring and version management:
        - section: Document section (Introduction, Methods, Results, etc.)
        - quality_score: Chunk quality (0-1 range)
        - word_count: Number of words in chunk
        - has_equations: Boolean flag for mathematical content
        - has_figures: Boolean flag for figure/table content
        - extraction_version: Version number for incremental updates
        """
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
                name="content_type",
                dtype=DataType.VARCHAR,
                max_length=32,
                description="Content type: image/table/text"
            ),
            FieldSchema(
                name="page_num",
                dtype=DataType.INT32,
                description="Page number"
            ),
            
            # New metadata fields (per D-06, lines 384-402 in CONTEXT.md)
            FieldSchema(
                name="section",
                dtype=DataType.VARCHAR,
                max_length=64,
                description="Document section: Introduction/Methods/Results/etc."
            ),
            FieldSchema(
                name="quality_score",
                dtype=DataType.FLOAT,
                description="Chunk quality score (0-1 range)"
            ),
            FieldSchema(
                name="word_count",
                dtype=DataType.INT32,
                description="Number of words in chunk"
            ),
            FieldSchema(
                name="has_equations",
                dtype=DataType.BOOL,
                description="Contains mathematical equations"
            ),
            FieldSchema(
                name="has_figures",
                dtype=DataType.BOOL,
                description="Contains figures or charts"
            ),
            FieldSchema(
                name="extraction_version",
                dtype=DataType.INT32,
                description="Extraction version for incremental updates"
            ),
            
            FieldSchema(
                name="content_data",
                dtype=DataType.VARCHAR,
                max_length=2048,
                description="Caption, description, or text snippet"
            ),
            FieldSchema(
                name="raw_data",
                dtype=DataType.JSON,
                description="Raw data: bbox for images, headers/rows for tables"
            ),
            FieldSchema(
                name="embedding",
                dtype=DataType.FLOAT_VECTOR,
                dim=self.embedding_dim,
                description="1024-dim BGE-M3 embedding"
            ),
        ]

        collection = self._create_collection_schema("paper_contents", fields)
        self._create_index(collection, "embedding")
        collection.load()

        logger.info(
            "Created paper_contents collection with enhanced schema",
            embedding_dim=self.embedding_dim,
            metadata_fields=6
        )
        return collection

    def insert_contents(self, data: List[Dict[str, Any]]) -> List[int]:
        """Insert content embeddings with enhanced metadata (per D-06).

        Args:
            data: List of content items with:
                - paper_id: Paper UUID
                - user_id: User UUID
                - content_type: 'image' | 'table' | 'text'
                - page_num: Page number
                - section: Document section (optional)
                - text: Content text (optional, for quality scoring)
                - content_data: Caption/description/text
                - raw_data: JSON with type-specific data
                - embedding: 1024-dim vector
                - has_equations: Boolean (optional)
                - has_figures: Boolean (optional)

        Returns:
            List of inserted IDs
        """
        collection = self.get_collection(settings.MILVUS_COLLECTION_CONTENTS)

        # Prepare enhanced data with metadata (per D-06)
        entities = []
        for item in data:
            # Calculate quality score
            quality_score = calculate_chunk_quality(item)
            
            entities.append({
                "paper_id": item["paper_id"],
                "user_id": item["user_id"],
                "content_type": item.get("content_type", "text"),
                "page_num": item.get("page_num", 0),
                
                # New metadata fields (per D-06)
                "section": item.get("section", ""),
                "quality_score": quality_score,
                "word_count": len(item.get("text", "").split()),
                "has_equations": bool(item.get("has_equations", False)),
                "has_figures": bool(item.get("has_figures", False)),
                "extraction_version": 2,  # Incremented per D-06
                
                "content_data": item.get("content_data", item.get("text", "")),
                "raw_data": item.get("raw_data", {}),
                "embedding": item["embedding"],
            })

        ids = collection.insert(entities)
        collection.flush()
        logger.info(
            f"Inserted {len(entities)} content items with enhanced metadata",
            avg_quality=sum(e["quality_score"] for e in entities) / len(entities) if entities else 0
        )
        return ids.primary_keys

    def insert_contents_batched(
        self,
        data: List[Dict[str, Any]],
        batch_size: int = 50,
        max_retries: int = 3
    ) -> List[int]:
        """Insert content embeddings in small batches with retry logic.
        
        Per D-27: 50-vector batches for reliability.
        Per D-28: Avoid single large insert that loses all data on failure.
        Per D-29: Exponential backoff retry (1s, 2s, 4s).
        
        Args:
            data: List of content items with embeddings
            batch_size: Vectors per batch (default 50 per D-27)
            max_retries: Max retry attempts per batch (default 3 per D-29)
            
        Returns:
            List of inserted IDs (may be partial if some batches failed)
        """
        collection = self.get_collection(settings.MILVUS_COLLECTION_CONTENTS_V2)
        all_ids = []
        
        # Process in batches
        total_batches = (len(data) + batch_size - 1) // batch_size
        
        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            
            retries = 0
            while retries < max_retries:
                try:
                    # Prepare entities with quality scoring
                    entities = []
                    for idx, item in enumerate(batch):
                        quality_score = calculate_chunk_quality(item)
                        
                        page_num = item.get("page_num", 0)
                        if page_num is None:
                            page_num = 0
                        if isinstance(page_num, list):
                            page_num = page_num[0] if page_num else 0
                        
                        entity = {
                            "paper_id": item["paper_id"],
                            "user_id": item["user_id"],
                            "content_type": item.get("content_type", "text"),
                            "page_num": int(page_num),
                            "section": item.get("section", ""),
                            "quality_score": float(quality_score),
                            "word_count": int(len(item.get("text", "").split())),
                            "has_equations": bool(item.get("has_equations", False)),
                            "has_figures": bool(item.get("has_figures", False)),
                            "extraction_version": 2,
                            "content_data": str(item.get("content_data", item.get("text", "")))[:8000],
                            "raw_data": item.get("raw_data", {}),
                            "embedding": item["embedding"],
                        }
                        entities.append(entity)
                    
                    logger.debug(
                        "Prepared entities for insert",
                        batch=batch_num,
                        count=len(entities),
                        page_nums=[e["page_num"] for e in entities]
                    )
                    
                    ids = collection.insert(entities)
                    all_ids.extend(ids.primary_keys)
                    
                    logger.debug(
                        "Milvus batch inserted",
                        batch=f"{batch_num}/{total_batches}",
                        count=len(entities)
                    )
                    break
                    
                except Exception as e:
                    retries += 1
                    delay = 2 ** retries  # 2s, 4s, 8s (exponential backoff per D-29)
                    
                    logger.warning(
                        "Milvus batch insert failed, retrying",
                        batch=f"{batch_num}/{total_batches}",
                        attempt=retries,
                        max_retries=max_retries,
                        delay=delay,
                        error=str(e)
                    )
                    
                    if retries >= max_retries:
                        logger.error(
                            "Milvus batch insert failed after max retries",
                            batch=f"{batch_num}/{total_batches}",
                            error=str(e)
                        )
                        # Record failure but continue with other batches
                        # Per D-28: Don't fail entire operation on one batch
                    else:
                        time.sleep(delay)
        
        # Flush all inserted data
        if all_ids:
            collection.flush()
        
        logger.info(
            "Milvus batch insert complete",
            total_items=len(data),
            inserted=len(all_ids),
            batches=total_batches
        )
        
        return all_ids

    def search_contents(
        self,
        embedding: List[float],
        user_id: Optional[str] = None,
        content_type: Optional[str] = None,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """Search unified paper_contents collection.

        Args:
            embedding: 1024-dim query embedding
            user_id: Optional user filter
            content_type: Optional content type filter ('image'/'table'/'text')
            top_k: Number of results

        Returns:
            List of content items with distance scores
        """
        collection = self.get_collection(settings.MILVUS_COLLECTION_CONTENTS)

        search_params = {
            "metric_type": "COSINE",
            "params": {"nprobe": 10}
        }

        # Build expression for filtering
        conditions = []
        if user_id:
            conditions.append(f"user_id == '{user_id}'")
        if content_type:
            conditions.append(f"content_type == '{content_type}'")

        expr = " and ".join(conditions) if conditions else None

        results = collection.search(
            data=[embedding],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            expr=expr,
            output_fields=[
                "paper_id", "page_num", "content_type",
                "content_data", "raw_data"
            ]
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
                    "content_type": hit.entity.get("content_type"),
                    "content_data": hit.entity.get("content_data"),
                    "raw_data": hit.entity.get("raw_data"),
                })
        return formatted

    def search_contents_v2(
        self,
        embedding: List[float],
        user_id: Optional[str] = None,
        content_type: Optional[str] = None,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """Search paper_contents_v2 collection with 2048-dim embeddings.

        Args:
            embedding: 2048-dim query embedding (Qwen3VL)
            user_id: Optional user filter
            content_type: Optional content type filter ('image'/'table'/'text')
            top_k: Number of results

        Returns:
            List of content items with distance scores
        """
        collection = self.get_collection(settings.MILVUS_COLLECTION_CONTENTS_V2)

        search_params = {
            "metric_type": "COSINE",
            "params": {"nprobe": 10}
        }

        conditions = []
        if user_id:
            conditions.append(f"user_id == '{user_id}'")
        if content_type:
            conditions.append(f"content_type == '{content_type}'")

        expr = " and ".join(conditions) if conditions else None

        results = collection.search(
            data=[embedding],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            expr=expr,
            output_fields=[
                "paper_id", "page_num", "content_type", "section",
                "content_data", "raw_data", "quality_score"
            ]
        )

        formatted = []
        for hits in results:
            for hit in hits:
                formatted.append({
                    "id": hit.id,
                    "distance": hit.distance,
                    "score": 1 - hit.distance,
                    "paper_id": hit.entity.get("paper_id"),
                    "page_num": hit.entity.get("page_num"),
                    "content_type": hit.entity.get("content_type"),
                    "section": hit.entity.get("section"),
                    "content_data": hit.entity.get("content_data"),
                    "raw_data": hit.entity.get("raw_data"),
                    "quality_score": hit.entity.get("quality_score"),
                })
        return formatted

    def delete_by_paper_contents(self, paper_id: str) -> None:
        """Delete all content entries for a paper.

        Args:
            paper_id: Paper UUID
        """
        collection = self.get_collection(settings.MILVUS_COLLECTION_CONTENTS)
        collection.delete(f'paper_id == "{paper_id}"')
        collection.flush()
        logger.info(f"Deleted content entries for paper {paper_id}")


# Singleton instance
_milvus_service: Optional[MilvusService] = None


def get_milvus_service() -> MilvusService:
    """Get or create MilvusService singleton."""
    global _milvus_service
    if _milvus_service is None:
        _milvus_service = MilvusService()
    return _milvus_service
