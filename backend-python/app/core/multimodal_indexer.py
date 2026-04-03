"""Multimodal indexer for orchestrating image and table extraction.

Provides:
- Orchestration of image extraction, captioning, and indexing
- Orchestration of table extraction, description generation, and indexing
- S3 upload for extracted images
- 1024-dim embedding generation via BGE-M3
- Milvus unified collection storage
- Partial failure tracking
- Reference context extraction for figures/tables (D-04)
"""

import gc
import re
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


def extract_figure_references(
    markdown: str,
    figure_label: str,
    figure_type: str = "figure"
) -> List[str]:
    """Extract reference contexts for figures/tables per D-04.

    Extracts text segments that reference a specific figure or table,
    providing contextual information about how the figure/table is discussed
    in the paper.

    Args:
        markdown: Full document markdown text
        figure_label: Figure/table label (e.g., "1", "2")
        figure_type: "figure" or "table"

    Returns:
        List of reference contexts (max 3), each containing text that
        mentions the figure/table.

    Example:
        >>> markdown = "As shown in Figure 1, the results are significant."
        >>> contexts = extract_figure_references(markdown, "1", "figure")
        >>> len(contexts) <= 3
        True
    """
    # Regex patterns for figure/table references (per D-04)
    if figure_type.lower() == "table":
        patterns = [
            rf"(Table\s*{figure_label}.*?)(?=Table\s*\d+|Figure|$)",
            rf"(表\s*{figure_label}.*?)(?=表\s*\d+|图|$)",
        ]
    else:  # figure
        patterns = [
            rf"(Figure\s*{figure_label}.*?)(?=Figure\s*\d+|Table|$)",
            rf"(图\s*{figure_label}.*?)(?=图\s*\d+|表|$)",
        ]

    contexts = []
    for pattern in patterns:
        matches = re.findall(pattern, markdown, re.DOTALL | re.IGNORECASE)
        contexts.extend(matches)

    # Limit to 3 context fragments (per D-04)
    return contexts[:3]


async def create_enhanced_multimodal_embedding(
    figure_type: str,  # "image" or "table"
    figure_label: str,
    caption: str,
    markdown: str,
    bge_m3_service,
    vlm_description: Optional[str] = None
) -> tuple[List[float], str]:
    """Create enhanced multimodal embedding per D-04.

    Combines caption, reference context, and optional VLM description
    to create a rich embedding for figures and tables.

    Args:
        figure_type: "image" or "table"
        figure_label: Figure/table number (e.g., "1", "2")
        caption: Figure/table caption
        markdown: Full document markdown for context extraction
        bge_m3_service: BGE-M3 service for embedding
        vlm_description: Optional VLM-generated description

    Returns:
        Tuple of (embedding, combined_text) where:
        - embedding: 1024-dim vector
        - combined_text: Text used for embedding (caption + context + description)

    Example:
        >>> embedding, text = await create_enhanced_multimodal_embedding(
        ...     "image", "1", "Figure 1: Results", markdown, bge_m3
        ... )
        >>> len(embedding)
        1024
    """
    # Extract reference contexts (per D-04)
    reference_contexts = extract_figure_references(
        markdown,
        figure_label,
        figure_type
    )

    # Limit context to 500 characters (LOCKED per D-04)
    context_text = " ".join(reference_contexts)[:500]

    # Combine parts (per D-04 lines 259-282 in CONTEXT.md)
    parts = [f"{figure_type.capitalize()} {figure_label}: {caption}"]

    if context_text:
        parts.append(f"Context: {context_text}")

    if vlm_description:
        parts.append(f"Description: {vlm_description}")

    combined_text = "\n\n".join(parts)

    # Generate embedding
    embedding = bge_m3_service.encode_text(combined_text)

    return embedding, combined_text


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
        parsed_items: List[Dict[str, Any]],
        paper_markdown: Optional[str] = None
    ) -> Dict[str, Any]:
        """Index all multimodal content from a paper.

        Args:
            paper_id: UUID of the paper
            user_id: UUID of the user
            pdf_path: Path to the PDF file
            parsed_items: List of parsed items from Docling
            paper_markdown: Full document markdown for reference context (D-04)

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
                paper_id, user_id, pdf_path, parsed_items, paper_markdown
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
                paper_id, user_id, parsed_items, paper_markdown
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
        parsed_items: List[Dict[str, Any]],
        paper_markdown: Optional[str] = None
    ) -> Dict[str, Any]:
        """Index images from the paper.

        Args:
            paper_id: UUID of the paper
            user_id: UUID of the user
            pdf_path: Path to the PDF file
            parsed_items: List of parsed items from Docling
            paper_markdown: Full document markdown for reference context (D-04)

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
                    paper_id, user_id, image_data, idx, paper_markdown
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
        idx: int,
        paper_markdown: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Process a single image.

        Args:
            paper_id: UUID of the paper
            user_id: UUID of the user
            image_data: ImageData object
            idx: Index for naming
            paper_markdown: Full document markdown for reference context (D-04)

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

        # Create enhanced embedding with reference context (per D-04)
        try:
            if paper_markdown:
                embedding, content_data = await create_enhanced_multimodal_embedding(
                    figure_type="image",
                    figure_label=str(idx + 1),
                    caption=caption,
                    markdown=paper_markdown,
                    bge_m3_service=self.bge_m3,
                    vlm_description=None  # Can add VLM description later
                )
            else:
                # Fallback to simple embedding if markdown not available
                embedding = self.bge_m3.encode_text(caption)
                content_data = caption
        except Exception as e:
            logger.error(
                "Failed to create enhanced embedding",
                page=image_data.page_num,
                error=str(e)
            )
            embedding = [0.0] * self.EMBEDDING_DIM
            content_data = caption

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
            "content_data": content_data,
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
        parsed_items: List[Dict[str, Any]],
        paper_markdown: Optional[str] = None
    ) -> Dict[str, Any]:
        """Index tables from the paper.

        Args:
            paper_id: UUID of the paper
            user_id: UUID of the user
            parsed_items: List of parsed items from Docling
            paper_markdown: Full document markdown for reference context (D-04)

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
                    paper_id, user_id, table_data, paper_markdown
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
        table_data: Any,
        paper_markdown: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Process a single table.

        Args:
            paper_id: UUID of the paper
            user_id: UUID of the user
            table_data: TableData object
            paper_markdown: Full document markdown for reference context (D-04)

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

        # Create enhanced embedding with reference context (per D-04)
        try:
            if paper_markdown:
                # Extract table number from markdown or use index
                table_label = self._extract_table_label(table_data.markdown)
                embedding, enhanced_content = await create_enhanced_multimodal_embedding(
                    figure_type="table",
                    figure_label=table_label,
                    caption=caption if caption else content_data,
                    markdown=paper_markdown,
                    bge_m3_service=self.bge_m3,
                    vlm_description=description
                )
                content_data = enhanced_content
            else:
                # Fallback to simple embedding
                embedding = self.bge_m3.encode_text(content_data)
        except Exception as e:
            logger.error(
                "Failed to create enhanced embedding",
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

    def _extract_table_label(self, table_markdown: str) -> str:
        """Extract table label from markdown.

        Args:
            table_markdown: Markdown containing table

        Returns:
            Table label (e.g., "1", "2") or "1" as default
        """
        import re
        # Try to extract table number from markdown
        match = re.search(r'Table\s*(\d+)', table_markdown, re.IGNORECASE)
        if match:
            return match.group(1)
        match = re.search(r'表\s*(\d+)', table_markdown)
        if match:
            return match.group(1)
        # Default to "1"
        return "1"


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
