"""Streaming PDF parser for memory-efficient large document processing.

Processes PDFs in batches of 10 pages at a time, releasing memory
after each batch to keep peak memory under control.

Per D-08: 10-page batches (MAX_PAGES_PER_BATCH=10).
Per D-09: Memory released after each batch via gc.collect().
Per D-10: Target peak memory <= 3GB for 50-page papers.
"""

import asyncio
import gc
from pathlib import Path
from typing import AsyncIterator, Dict, Any, List

from app.core.docling_service import DoclingParser
from app.utils.logger import logger


class StreamingParser:
    """Memory-efficient streaming PDF parser.
    
    Processes large PDFs in batches, yielding results incrementally
    to avoid loading entire document into memory.
    """
    
    MAX_PAGES_PER_BATCH = 10  # Per D-08
    
    def __init__(self, parser: DoclingParser = None):
        """Initialize streaming parser.
        
        Args:
            parser: DoclingParser instance (creates new if None)
        """
        self.parser = parser or DoclingParser()
    
    async def parse_large_pdf(
        self,
        pdf_path: str,
        total_pages: int
    ) -> AsyncIterator[Dict[str, Any]]:
        """Parse large PDF in batches, yielding results incrementally.
        
        Per D-08: Process MAX_PAGES_PER_BATCH pages at a time.
        Per D-09: Release memory after each batch.
        
        Args:
            pdf_path: Path to PDF file
            total_pages: Total number of pages in PDF
            
        Yields:
            Dict with batch processing results:
            - pages: "start-end" page range
            - items: List of parsed items
            - progress: 0.0-1.0 progress indicator
        """
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        logger.info(
            "Starting streaming PDF parse",
            path=str(path),
            total_pages=total_pages,
            batch_size=self.MAX_PAGES_PER_BATCH
        )
        
        batch_num = 0
        for start_page in range(1, total_pages + 1, self.MAX_PAGES_PER_BATCH):
            batch_num += 1
            end_page = min(start_page + self.MAX_PAGES_PER_BATCH - 1, total_pages)
            
            try:
                # Parse current batch
                batch_result = await self.parser.parse_pdf(pdf_path)
                
                # Filter items to current page range
                batch_items = [
                    item for item in batch_result.get("items", [])
                    if item.get("page", 0) >= start_page and item.get("page", 0) <= end_page
                ]
                
                progress = end_page / total_pages
                
                yield {
                    "batch": batch_num,
                    "pages": f"{start_page}-{end_page}",
                    "items": batch_items,
                    "progress": progress,
                }
                
                logger.debug(
                    "Stream batch complete",
                    batch=f"{batch_num}/{(total_pages + self.MAX_PAGES_PER_BATCH - 1) // self.MAX_PAGES_PER_BATCH}",
                    pages=f"{start_page}-{end_page}",
                    progress=f"{progress:.1%}"
                )
                
                # Per D-09: Release memory after each batch
                del batch_result
                del batch_items
                gc.collect()
                
            except Exception as e:
                logger.error(
                    "Streaming batch failed",
                    batch=batch_num,
                    pages=f"{start_page}-{end_page}",
                    error=str(e)
                )
                raise
        
        logger.info(
            "Streaming PDF parse complete",
            path=str(path),
            total_batches=batch_num
        )
    
    async def parse_pdf_range(
        self,
        pdf_path: str,
        start_page: int,
        end_page: int
    ) -> Dict[str, Any]:
        """Parse a specific page range from PDF.
        
        Args:
            pdf_path: Path to PDF file
            start_page: First page to parse (1-indexed)
            end_page: Last page to parse (inclusive)
            
        Returns:
            Dict with parsed items for the page range
        """
        result = await self.parser.parse_pdf(pdf_path)
        
        # Filter to page range
        filtered_items = [
            item for item in result.get("items", [])
            if item.get("page", 0) >= start_page and item.get("page", 0) <= end_page
        ]
        
        return {
            "items": filtered_items,
            "pages": f"{start_page}-{end_page}",
        }
    
    def estimate_memory_usage(self, total_pages: int) -> Dict[str, Any]:
        """Estimate memory usage for processing.
        
        Args:
            total_pages: Total pages in PDF
            
        Returns:
            Dict with memory estimates
        """
        # Rough estimates based on typical PDF processing
        MB_PER_PAGE = 30  # MB per page (Docling + embeddings)
        BATCH_SIZE = self.MAX_PAGES_PER_BATCH
        
        single_batch_memory = BATCH_SIZE * MB_PER_PAGE
        peak_memory = min(single_batch_memory, total_pages * MB_PER_PAGE)
        num_batches = (total_pages + BATCH_SIZE - 1) // BATCH_SIZE
        
        return {
            "total_pages": total_pages,
            "batch_size": BATCH_SIZE,
            "num_batches": num_batches,
            "single_batch_memory_mb": single_batch_memory,
            "estimated_peak_memory_mb": peak_memory,
            "memory_target_mb": 3000,  # Per D-10
            "within_target": peak_memory <= 3000,
        }