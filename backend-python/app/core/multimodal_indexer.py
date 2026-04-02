"""Multimodal indexer for orchestrating image and table extraction.

Provides:
- Orchestration of image extraction, captioning, and indexing
- Orchestration of table extraction, description generation, and indexing
- S3 upload for extracted images
- 1024-dim embedding generation via BGE-M3
- Milvus unified collection storage
- Partial failure tracking
"""

import gc
from io import BytesIO
from typing import Dict, List, Optional, Any

from PIL import Image

from app.core.image_extractor import ImageExtractor
from app.core.table_extractor import TableExtractor
from app.core.image_caption_service import get_image_caption_service
from app.core.table_description_service import get_table_description_service
from app.core.bge_m3_service import get_bge_m3_service
from app.core.milvus_service import get_milvus_service
from app.core.storage import ObjectStorage
from app.utils.logger import logger


class MultimodalIndexer:
    """Orchestrate multimodal content extraction and indexing.

    Coordinates image extraction, caption generation, embedding creation,
    S3 storage, and Milvus indexing for academic papers.
    """

    EMBEDDING_DIM = 1024

    def __init__(self):
        """Initialize the multimodal indexer."""
        self.image_extractor = ImageExtractor()
        self.table_extractor = TableExtractor()
        self.caption_service = get_image_caption_service()
        self.description_service = get_table_description_service()
        self.bge_m3 = get_bge_m3_service()
        self.milvus = get_milvus_service()
        self.storage = ObjectStorage()

    async def index_paper(
        self,
        paper_id: str,
        user_id: str,
        pdf_path: str,
        parsed_items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Index all multimodal content from a paper.

        Args:
            paper_id: UUID of the paper
            user_id: UUID of the user
            pdf_path: Path to the PDF file
            parsed_items: List of parsed items from Docling

        Returns:
            Dictionary with indexing results:
            - images_indexed: Number of images indexed
            - tables_indexed: Number of tables indexed
            - partial_failures: List of failure records
        """
        results = {
            "images_indexed": 0,
            "tables_indexed": 0,
            "partial_failures": []
        }

        # Index images
        try:
            image_results = await self._index_images(
                paper_id, user_id, pdf_path, parsed_items
            )
            results["images_indexed"] = image_results["count"]
            results["partial_failures"].extend(image_results["failures"])
        except Exception as e:
            logger.error(
                "Image indexing failed",
                paper_id=paper_id,
                error=str(e)
            )
            results["partial_failures"].append({
                "type": "image_batch",
                "error": str(e)
            })

        # Index tables
        try:
            table_results = await self._index_tables(
                paper_id, user_id, parsed_items
            )
            results["tables_indexed"] = table_results["count"]
            results["partial_failures"].extend(table_results["failures"])
        except Exception as e:
            logger.error(
                "Table indexing failed",
                paper_id=paper_id,
                error=str(e)
            )
            results["partial_failures"].append({
                "type": "table_batch",
                "error": str(e)
            })

        logger.info(
            "Multimodal indexing complete",
            paper_id=paper_id,
            images_indexed=results["images_indexed"],
            tables_indexed=results["tables_indexed"],
            failures=len(results["partial_failures"])
        )

        return results

    async def _index_images(
        self,
        paper_id: str,
        user_id: str,
        pdf_path: str,
        parsed_items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Index images from the paper.

        Args:
            paper_id: UUID of the paper
            user_id: UUID of the user
            pdf_path: Path to the PDF file
            parsed_items: List of parsed items from Docling

        Returns:
            Dictionary with count and failures
        """
        results = {"count": 0, "failures": []}

        # Extract images from PDF
        image_data_list = self.image_extractor.extract_images_from_pdf(
            pdf_path, parsed_items
        )

        if not image_data_list:
            logger.debug("No images found in paper", paper_id=paper_id)
            return results

        logger.info(
            "Found images to index",
            paper_id=paper_id,
            image_count=len(image_data_list)
        )

        # Process each image
        milvus_entries = []
        for idx, image_data in enumerate(image_data_list):
            try:
                entry = await self._process_single_image(
                    paper_id, user_id, image_data, idx
                )
                if entry:
                    milvus_entries.append(entry)
                    results["count"] += 1

                # Periodic garbage collection
                if idx % 5 == 0:
                    gc.collect()

            except Exception as e:
                logger.warning(
                    "Failed to process image",
                    paper_id=paper_id,
                    page=image_data.page_num,
                    error=str(e)
                )
                results["failures"].append({
                    "type": "image",
                    "page": image_data.page_num,
                    "error": str(e)
                })

        # Insert into Milvus
        if milvus_entries:
            try:
                self.milvus.insert_contents(milvus_entries)
                logger.info(
                    "Inserted images to Milvus",
                    paper_id=paper_id,
                    count=len(milvus_entries)
                )
            except Exception as e:
                logger.error(
                    "Failed to insert images to Milvus",
                    paper_id=paper_id,
                    error=str(e)
                )
                results["failures"].append({
                    "type": "image_milvus_insert",
                    "error": str(e)
                })

        return results

    async def _process_single_image(
        self,
        paper_id: str,
        user_id: str,
        image_data: Any,
        idx: int
    ) -> Optional[Dict[str, Any]]:
        """Process a single image.

        Args:
            paper_id: UUID of the paper
            user_id: UUID of the user
            image_data: ImageData object
            idx: Index for naming

        Returns:
            Dictionary ready for Milvus insertion, or None on failure
        """
        # Generate caption
        try:
            caption = await self.caption_service.generate_caption(
                image_data.image,
                max_length=100
            )
        except Exception as e:
            logger.warning(
                "Caption generation failed, using fallback",
                page=image_data.page_num,
                error=str(e)
            )
            caption = "Figure showing research data"

        # Encode caption to 1024-dim vector
        try:
            embedding = self.bge_m3.encode_text(caption)
        except Exception as e:
            logger.error(
                "Failed to encode caption",
                page=image_data.page_num,
                error=str(e)
            )
            embedding = [0.0] * self.EMBEDDING_DIM

        # Upload image to S3
        storage_key = f"images/{user_id}/{paper_id}/p{image_data.page_num}_{idx}.png"
        try:
            # Convert PIL image to bytes
            buffer = BytesIO()
            image_data.image.save(buffer, format='PNG')
            image_bytes = buffer.getvalue()

            await self.storage.upload_image_bytes(
                storage_key,
                image_bytes,
                content_type="image/png"
            )
        except Exception as e:
            logger.warning(
                "Failed to upload image to S3, continuing",
                storage_key=storage_key,
                error=str(e)
            )
            storage_key = None

        # Prepare Milvus entry
        entry = {
            "paper_id": paper_id,
            "user_id": user_id,
            "page_num": image_data.page_num,
            "content_type": "image",
            "content_data": caption,
            "raw_data": {
                "bbox": image_data.bbox,
                "storage_key": storage_key,
            },
            "embedding": embedding,
        }

        # Close image to free memory
        image_data.image.close()

        return entry

    async def _index_tables(
        self,
        paper_id: str,
        user_id: str,
        parsed_items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Index tables from the paper.

        Args:
            paper_id: UUID of the paper
            user_id: UUID of the user
            parsed_items: List of parsed items from Docling

        Returns:
            Dictionary with count and failures
        """
        results = {"count": 0, "failures": []}

        # Extract tables
        table_data_list = self.table_extractor.extract_tables_from_pdf(parsed_items)

        if not table_data_list:
            logger.debug("No tables found in paper", paper_id=paper_id)
            return results

        logger.info(
            "Found tables to index",
            paper_id=paper_id,
            table_count=len(table_data_list)
        )

        # Process each table
        milvus_entries = []
        for table_data in table_data_list:
            try:
                entry = await self._process_single_table(
                    paper_id, user_id, table_data
                )
                if entry:
                    milvus_entries.append(entry)
                    results["count"] += 1
            except Exception as e:
                logger.warning(
                    "Failed to process table",
                    paper_id=paper_id,
                    page=table_data.page_num,
                    error=str(e)
                )
                results["failures"].append({
                    "type": "table",
                    "page": table_data.page_num,
                    "error": str(e)
                })

        # Insert into Milvus
        if milvus_entries:
            try:
                self.milvus.insert_contents(milvus_entries)
                logger.info(
                    "Inserted tables to Milvus",
                    paper_id=paper_id,
                    count=len(milvus_entries)
                )
            except Exception as e:
                logger.error(
                    "Failed to insert tables to Milvus",
                    paper_id=paper_id,
                    error=str(e)
                )
                results["failures"].append({
                    "type": "table_milvus_insert",
                    "error": str(e)
                })

        return results

    async def _process_single_table(
        self,
        paper_id: str,
        user_id: str,
        table_data: Any
    ) -> Optional[Dict[str, Any]]:
        """Process a single table.

        Args:
            paper_id: UUID of the paper
            user_id: UUID of the user
            table_data: TableData object

        Returns:
            Dictionary ready for Milvus insertion, or None on failure
        """
        # Extract caption from markdown
        caption = self.table_extractor._extract_caption(table_data.markdown)

        # Generate description
        description = None
        try:
            description = await self.description_service.generate_description(
                caption=caption,
                headers=table_data.headers,
                sample_rows=table_data.rows[:3]
            )
        except Exception as e:
            logger.warning(
                "Description generation failed, using caption",
                page=table_data.page_num,
                error=str(e)
            )

        # Use caption as fallback
        content_data = description if description else caption
        if not content_data:
            content_data = f"Table with {len(table_data.headers)} columns"

        # Encode to 1024-dim vector
        try:
            embedding = self.bge_m3.encode_text(content_data)
        except Exception as e:
            logger.error(
                "Failed to encode table content",
                page=table_data.page_num,
                error=str(e)
            )
            embedding = [0.0] * self.EMBEDDING_DIM

        # Prepare Milvus entry
        entry = {
            "paper_id": paper_id,
            "user_id": user_id,
            "page_num": table_data.page_num,
            "content_type": "table",
            "content_data": content_data,
            "raw_data": {
                "headers": table_data.headers,
                "row_count": len(table_data.rows),
            },
            "embedding": embedding,
        }

        return entry


# Singleton instance
_multimodal_indexer: Optional[MultimodalIndexer] = None


def get_multimodal_indexer() -> MultimodalIndexer:
    """Get or create MultimodalIndexer singleton."""
    global _multimodal_indexer
    if _multimodal_indexer is None:
        _multimodal_indexer = MultimodalIndexer()
    return _multimodal_indexer


async def create_multimodal_indexer() -> MultimodalIndexer:
    """Create and initialize MultimodalIndexer.

    Returns:
        MultimodalIndexer instance
    """
    return get_multimodal_indexer()
