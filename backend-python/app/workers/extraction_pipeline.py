"""Parallel extraction pipeline for PDF processing.

Executes 4 extraction tasks in parallel:
1. IMRaD extraction (CPU-bound)
2. Metadata extraction (CPU-bound)
3. Image extraction + embedding (CPU + GPU)
4. Table extraction + embedding (CPU + GPU)

Per D-04: Four-stage parallel extraction.
Per D-07: ThreadPoolExecutor with max_workers=4.
Per D-12-D-15: Strict error handling (critical stages block, auxiliary stages degrade).
"""

import asyncio
import gc
import re
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from typing import Any, Dict, List, Optional

from app.workers.pipeline_context import PipelineContext
from app.core.imrad_extractor import extract_imrad_enhanced, extract_metadata
from app.core.qwen3vl_service import get_qwen3vl_service
from app.core.image_extractor import ImageExtractor
from app.core.table_extractor import TableExtractor
from app.core.storage import ObjectStorage
from app.utils.logger import logger


class PipelineError(Exception):
    """Raised when a critical pipeline stage fails."""
    pass


class ExtractionPipeline:
    """Parallel extraction pipeline for PDF content.

    Uses ThreadPoolExecutor for CPU-bound tasks (IMRaD, metadata)
    while keeping GPU-bound tasks (embedding) in async context.
    """

    EMBEDDING_DIM = 2048  # Qwen3VL dimension

    def __init__(self, max_workers: int = 4):
        """Initialize extraction pipeline.

        Args:
            max_workers: Number of parallel workers per D-07
        """
        self.executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="extraction_worker"
        )
        self.qwen3vl = get_qwen3vl_service()
        self.image_extractor = ImageExtractor()
        self.table_extractor = TableExtractor()
        self.storage = ObjectStorage()

    async def extract(self, ctx: PipelineContext) -> PipelineContext:
        """Execute all extraction tasks in parallel.

        Per D-04: IMRaD, metadata, images, tables run concurrently.
        Per D-12-D-15: Critical failures block, auxiliary failures degrade.

        Args:
            ctx: Pipeline context with parse_result populated

        Returns:
            Updated context with extraction results

        Raises:
            PipelineError: If critical stage (IMRaD or metadata) fails
        """
        logger.info("Starting parallel extraction", task_id=ctx.task_id)

        # Create parallel tasks
        loop = asyncio.get_event_loop()

        tasks = [
            self._extract_imrad(ctx, loop),
            self._extract_metadata(ctx, loop),
            self._extract_images_with_embedding(ctx, loop),
            self._extract_tables_with_embedding(ctx, loop),
        ]

        # Parallel execution with error handling
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Per D-12, D-13: Critical stages must succeed
        if isinstance(results[0], Exception):
            raise PipelineError(f"IMRaD extraction failed: {results[0]}")
        if isinstance(results[1], Exception):
            raise PipelineError(f"Metadata extraction failed: {results[1]}")

        # Store results
        ctx.imrad = results[0]
        ctx.metadata = results[1]

        # Per D-14, D-15: Auxiliary stage failures are logged but don't block
        ctx.image_results = results[2] if not isinstance(results[2], Exception) else []
        ctx.table_results = results[3] if not isinstance(results[3], Exception) else []

        # Log non-critical failures
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                stage_names = ["IMRaD", "Metadata", "Images", "Tables"]
                if i >= 2:  # Auxiliary stages
                    ctx.add_error(f"{stage_names[i]} extraction failed: {result}")
                    logger.warning(
                        "Auxiliary extraction failed",
                        task_id=ctx.task_id,
                        stage=stage_names[i],
                        error=str(result)
                    )

        logger.info(
            "Parallel extraction complete",
            task_id=ctx.task_id,
            has_imrad=ctx.imrad is not None,
            has_metadata=ctx.metadata is not None,
            images_count=len(ctx.image_results) if ctx.image_results else 0,
            tables_count=len(ctx.table_results) if ctx.table_results else 0
        )

        return ctx

    async def _extract_imrad(
        self,
        ctx: PipelineContext,
        loop: asyncio.AbstractEventLoop
    ) -> Dict[str, Any]:
        """Extract IMRaD structure (CPU-bound, runs in thread pool).

        Per D-05: Uses enhanced extraction with LLM assistance for low-confidence cases.
        """
        items = ctx.parse_result["items"]
        markdown = ctx.parse_result.get("markdown", "")

        # Run in thread pool (CPU-bound)
        result = await loop.run_in_executor(
            self.executor,
            lambda: asyncio.run(extract_imrad_enhanced(
                items=items,
                markdown=markdown,
                paper_metadata=extract_metadata(items)
            ))
        )

        logger.debug("IMRaD extraction complete", task_id=ctx.task_id)
        return result

    async def _extract_metadata(
        self,
        ctx: PipelineContext,
        loop: asyncio.AbstractEventLoop
    ) -> Dict[str, Any]:
        """Extract metadata (CPU-bound, runs in thread pool)."""
        items = ctx.parse_result["items"]

        # Run in thread pool (CPU-bound)
        result = await loop.run_in_executor(
            self.executor,
            lambda: extract_metadata(items)
        )

        logger.debug("Metadata extraction complete", task_id=ctx.task_id)
        return result

    async def _extract_images_with_embedding(
        self,
        ctx: PipelineContext,
        loop: asyncio.AbstractEventLoop
    ) -> List[Dict[str, Any]]:
        """Extract images and generate embeddings.

        Per D-01: Direct pixel encoding (no text conversion).
        """
        results = []

        # Step 1: Extract images (CPU-bound)
        images = await loop.run_in_executor(
            self.executor,
            self.image_extractor.extract_images_from_pdf,
            ctx.local_path,
            ctx.parse_result["items"]
        )

        if not images:
            logger.debug("No images found", task_id=ctx.task_id)
            return results

        logger.info(
            "Found images to process",
            task_id=ctx.task_id,
            count=len(images)
        )

        # Step 2: Generate embeddings for each image
        for idx, img_data in enumerate(images):
            try:
                # Per D-01: Direct pixel encoding with Qwen3VL
                embedding = self.qwen3vl.encode_image(img_data.image)

                # Upload to S3 (optional, non-blocking)
                storage_key = f"images/{ctx.user_id}/{ctx.paper_id}/p{img_data.page_num}_{idx}.png"
                try:
                    buffer = BytesIO()
                    img_data.image.save(buffer, format='PNG')
                    await self.storage.upload_image_bytes(
                        storage_key,
                        buffer.getvalue(),
                        content_type="image/png"
                    )
                except Exception as e:
                    logger.warning(
                        "Failed to upload image to S3",
                        storage_key=storage_key,
                        error=str(e)
                    )
                    storage_key = None

                results.append({
                    "paper_id": ctx.paper_id,
                    "user_id": ctx.user_id,
                    "page_num": img_data.page_num,
                    "content_type": "image",
                    "content_data": f"Figure on page {img_data.page_num}",
                    "embedding": embedding,
                    "raw_data": {
                        "bbox": img_data.bbox if hasattr(img_data, 'bbox') else None,
                        "storage_key": storage_key,
                    }
                })

                # Periodic garbage collection per D-10
                if idx % 5 == 0:
                    gc.collect()

            except Exception as e:
                logger.warning(
                    "Image embedding failed",
                    page=img_data.page_num,
                    error=str(e)
                )
                # Use zero-vector placeholder per D-15
                results.append({
                    "paper_id": ctx.paper_id,
                    "user_id": ctx.user_id,
                    "page_num": img_data.page_num,
                    "content_type": "image",
                    "content_data": f"Figure on page {img_data.page_num}",
                    "embedding": [0.0] * self.EMBEDDING_DIM,
                    "raw_data": {"error": str(e)}
                })

            finally:
                # Close image to free memory
                if hasattr(img_data, 'image') and img_data.image:
                    img_data.image.close()

        logger.info(
            "Image extraction complete",
            task_id=ctx.task_id,
            count=len(results)
        )

        return results

    async def _extract_tables_with_embedding(
        self,
        ctx: PipelineContext,
        loop: asyncio.AbstractEventLoop
    ) -> List[Dict[str, Any]]:
        """Extract tables and generate embeddings.

        Per D-02: Table serialization format for embedding.
        """
        results = []

        # Step 1: Extract tables (CPU-bound)
        tables = await loop.run_in_executor(
            self.executor,
            self.table_extractor.extract_tables_from_pdf,
            ctx.parse_result["items"]
        )

        if not tables:
            logger.debug("No tables found", task_id=ctx.task_id)
            return results

        logger.info(
            "Found tables to process",
            task_id=ctx.task_id,
            count=len(tables)
        )

        # Step 2: Generate embeddings for each table
        for table_data in tables:
            try:
                # Per D-02: Table serialization
                caption = ""
                headers = []
                rows = []

                if hasattr(table_data, 'markdown'):
                    # Extract caption from markdown
                    match = re.search(r'Table\s*\d+[:：]?\s*(.+)', table_data.markdown)
                    if match:
                        caption = match.group(1).strip()

                if hasattr(table_data, 'headers'):
                    headers = table_data.headers

                if hasattr(table_data, 'rows'):
                    rows = table_data.rows[:3]  # Max 3 rows per D-02

                # Generate embedding via Qwen3VL
                embedding = self.qwen3vl.encode_table(
                    caption=caption,
                    headers=headers,
                    rows=rows
                )

                # Build content data
                content_data = caption if caption else f"Table with {len(headers)} columns"

                results.append({
                    "paper_id": ctx.paper_id,
                    "user_id": ctx.user_id,
                    "page_num": table_data.page_num if hasattr(table_data, 'page_num') else 0,
                    "content_type": "table",
                    "content_data": content_data,
                    "embedding": embedding,
                    "raw_data": {
                        "headers": headers,
                        "rows": rows,
                    }
                })

            except Exception as e:
                logger.warning(
                    "Table embedding failed",
                    page=table_data.page_num if hasattr(table_data, 'page_num') else 0,
                    error=str(e)
                )
                # Use zero-vector placeholder per D-15
                results.append({
                    "paper_id": ctx.paper_id,
                    "user_id": ctx.user_id,
                    "page_num": table_data.page_num if hasattr(table_data, 'page_num') else 0,
                    "content_type": "table",
                    "content_data": "Table (embedding failed)",
                    "embedding": [0.0] * self.EMBEDDING_DIM,
                    "raw_data": {"error": str(e)}
                })

        logger.info(
            "Table extraction complete",
            task_id=ctx.task_id,
            count=len(results)
        )

        return results


# Singleton
_pipeline: Optional[ExtractionPipeline] = None


def get_extraction_pipeline() -> ExtractionPipeline:
    """Get or create ExtractionPipeline singleton."""
    global _pipeline
    if _pipeline is None:
        _pipeline = ExtractionPipeline()
    return _pipeline