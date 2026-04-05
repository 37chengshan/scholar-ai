"""Table extraction service for PDF documents.

Provides:
- Table extraction from Docling parsed items
- Markdown table parsing (headers, rows)
- 2048-dim embedding generation via Qwen3VL service (multimodal)
- Structured data output for Milvus storage
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

from app.core.qwen3vl_service import get_qwen3vl_service
from app.utils.logger import logger


@dataclass
class TableData:
    """Container for extracted table data."""
    page_num: int
    markdown: str
    headers: List[str]
    rows: List[Dict[str, str]]


class TableExtractor:
    """Extract tables from PDF documents and generate embeddings."""

    EMBEDDING_DIM = 2048  # Qwen3VL outputs 2048-dim

    def __init__(self):
        """Initialize the table extractor."""
        self._qwen3vl_service = None

    def _get_qwen3vl_service(self):
        """Lazy load Qwen3VL service."""
        if self._qwen3vl_service is None:
            self._qwen3vl_service = get_qwen3vl_service()
        return self._qwen3vl_service

    def extract_tables_from_pdf(
        self,
        docling_items: List[Dict[str, Any]]
    ) -> List[TableData]:
        """Extract tables from Docling parsed items.

        Args:
            docling_items: List of items from Docling parser

        Returns:
            List of TableData objects containing extracted tables
        """
        # Filter for table items
        table_items = [
            item for item in docling_items
            if item.get("type") == "table" and item.get("text")
        ]

        if not table_items:
            logger.debug("No table items found in document")
            return []

        extracted_tables = []

        for item in table_items:
            page_num = item.get("page", 1)
            markdown = item.get("text", "")

            # Parse markdown table
            headers, rows = self._parse_table_markdown(markdown)

            if not headers and not rows:
                logger.debug("Skipping malformed table", page_num=page_num)
                continue

            extracted_tables.append(TableData(
                page_num=page_num,
                markdown=markdown,
                headers=headers,
                rows=rows
            ))

            logger.debug(
                "Extracted table",
                page_num=page_num,
                headers_count=len(headers),
                rows_count=len(rows)
            )

        logger.info(
            "Table extraction complete",
            extracted_count=len(extracted_tables)
        )
        return extracted_tables

    def _parse_table_markdown(
        self,
        markdown: str
    ) -> tuple[List[str], List[Dict[str, str]]]:
        """Parse markdown table into headers and rows.

        Args:
            markdown: Markdown table text

        Returns:
            Tuple of (headers list, rows list of dicts)
        """
        if not markdown:
            return [], []

        # Split into lines and clean
        lines = markdown.strip().split('\n')
        lines = [line.strip() for line in lines if line.strip()]

        if len(lines) < 2:
            return [], []

        # Remove caption line if present (lines not starting with |)
        while lines and not lines[0].startswith('|'):
            lines = lines[1:]

        if len(lines) < 2:
            return [], []

        # Parse header row
        header_line = lines[0]
        headers = self._parse_table_row(header_line)

        # Skip separator line (---|---|---)
        if len(lines) > 1 and '---' in lines[1]:
            data_lines = lines[2:]
        else:
            data_lines = lines[1:]

        # Parse data rows
        rows = []
        for line in data_lines:
            if not line.startswith('|'):
                continue
            row_values = self._parse_table_row(line)
            if row_values:
                # Create dict from headers and values
                row_dict = {}
                for i, header in enumerate(headers):
                    if i < len(row_values):
                        row_dict[header] = row_values[i]
                    else:
                        row_dict[header] = ""
                rows.append(row_dict)

        return headers, rows

    def _parse_table_row(self, line: str) -> List[str]:
        """Parse a markdown table row into cell values.

        Args:
            line: Table row line (e.g., "| A | B | C |")

        Returns:
            List of cell values
        """
        if not line.startswith('|') or not line.endswith('|'):
            return []

        # Remove leading/trailing | and split
        content = line[1:-1]
        cells = [cell.strip() for cell in content.split('|')]
        return cells

    def _extract_caption(self, markdown: str) -> str:
        """Extract caption from markdown table.

        Looks for lines before the table that don't start with |.

        Args:
            markdown: Full markdown table text

        Returns:
            Caption string or empty string
        """
        lines = markdown.strip().split('\n')

        caption_lines = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith('|'):
                break
            caption_lines.append(line)

        return ' '.join(caption_lines).strip()

    async def generate_description_and_embed(
        self,
        table_data: TableData,
        paper_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Generate embedding for a table using Qwen3VL multimodal encoding.

        Args:
            table_data: TableData object containing the extracted table
            paper_id: UUID of the paper
            user_id: UUID of the user

        Returns:
            Dictionary ready for Milvus insertion with:
            - paper_id, user_id, page_num, content_type
            - content_data: serialized table representation
            - raw_data: headers, rows, row_count
            - embedding: 2048-dim vector
        """
        qwen3vl_service = self._get_qwen3vl_service()

        # Extract caption
        caption = self._extract_caption(table_data.markdown)

        # Serialize table for Qwen3VL encoding per D-01, D-02
        # Format: Table: {caption}\\nColumns: {headers}\\nSample data: {rows}
        serialized_table = f"Table: {caption}\nColumns: {', '.join(table_data.headers)}\nSample data: {table_data.rows[:3]}"

        # Direct table encoding via Qwen3VL
        try:
            embedding = qwen3vl_service.encode_table(
                caption=caption,
                headers=table_data.headers,
                rows=table_data.rows[:3]  # First 3 rows per D-02
            )
            logger.debug("Generated table embedding", dim=len(embedding))
        except Exception as e:
            logger.error("Failed to encode table", error=str(e))
            embedding = [0.0] * self.EMBEDDING_DIM

        return {
            "paper_id": paper_id,
            "user_id": user_id,
            "page_num": table_data.page_num,
            "content_type": "table",
            "content_data": serialized_table,  # Serialized table representation
            "raw_data": {
                "headers": table_data.headers,
                "row_count": len(table_data.rows),
            },
            "embedding": embedding,
        }

    async def process_pdf_tables(
        self,
        docling_items: List[Dict[str, Any]],
        paper_id: str,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """Process all tables from a PDF.

        Convenience method that extracts and embeds all tables.

        Args:
            docling_items: Docling parsed items
            paper_id: Paper UUID
            user_id: User UUID

        Returns:
            List of dictionaries ready for Milvus insertion
        """
        tables = self.extract_tables_from_pdf(docling_items)

        results = []
        for table_data in tables:
            try:
                result = await self.generate_description_and_embed(
                    table_data, paper_id, user_id
                )
                results.append(result)
            except Exception as e:
                logger.error(
                    "Failed to process table",
                    page_num=table_data.page_num,
                    error=str(e)
                )
                # Continue processing other tables

        return results
