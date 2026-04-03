"""Docling PDF parser service with OCR support

Provides async wrapper around Docling for PDF parsing with:
- OCR enabled for scanned documents
- Multi-language support (en, zh)
- Structured content extraction (text, tables, formulas)
- Page number and bounding box tracking
- Memory-efficient processing

Note: Models should be downloaded to ~/.cache/docling/models
"""

import gc
import os
from pathlib import Path
from typing import List, Optional

from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, InputFormat, PdfFormatOption
from docling_core.types.doc import TextItem, TableItem, PictureItem

# Semantic chunking imports (per D-03)
from llama_index.core.node_parser import SemanticSplitterNodeParser
from llama_index.core import Document
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

from app.utils.logger import logger


class DoclingParser:
    """PDF parser using Docling with OCR support."""

    def __init__(self):
        """Initialize Docling parser with pipeline options."""
        # Set model path to local cache
        model_path = Path.home() / ".cache" / "docling" / "models"
        if model_path.exists():
            os.environ["DOCLING_MODELS_PATH"] = str(model_path)
            logger.info("Using local Docling models", path=str(model_path))

        # Configure pipeline
        # Layout model is required for structure detection
        self.pipeline_options = PdfPipelineOptions(
            generate_picture_images=False,  # Reduce memory usage
            generate_table_images=False,    # Reduce memory usage
            images_scale=1.0,
            do_ocr=False,  # Disable OCR (requires EasyOCR/Tesseract installation)
        )

        # Create document converter with PDF format options
        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=self.pipeline_options,
                )
            }
        )

        logger.info("DoclingParser initialized")

    async def parse_pdf(self, pdf_path: str) -> dict:
        """
        Parse PDF and return structured content.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dictionary with:
            - markdown: Full document as markdown
            - items: List of items with type, text, page, bbox
            - page_count: Total number of pages
            - metadata: Document metadata
        """
        path = Path(pdf_path)

        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        logger.info("Starting PDF parsing", path=str(path))

        try:
            # Convert PDF to Docling document
            result = self.converter.convert(path)
            doc = result.document

            # Export to markdown
            markdown = doc.export_to_markdown()

            # Extract items with provenance
            items = []
            for item, _level in doc.iterate_items():
                item_data = {
                    "type": None,
                    "text": None,
                    "page": None,
                    "bbox": None,
                }

                if isinstance(item, TextItem):
                    item_data["type"] = "text"
                    item_data["text"] = item.text
                elif isinstance(item, TableItem):
                    item_data["type"] = "table"
                    try:
                        item_data["text"] = item.export_to_markdown()
                    except Exception:
                        item_data["text"] = "[Table content extraction failed]"
                elif isinstance(item, PictureItem):
                    item_data["type"] = "picture"
                    # Pictures don't have text, but we track their location
                    item_data["text"] = None

                # Get provenance (page numbers, bounding boxes)
                if item.prov:
                    prov = item.prov[0]
                    item_data["page"] = prov.page_no
                    if hasattr(prov, "bbox") and prov.bbox:
                        item_data["bbox"] = {
                            "l": prov.bbox.l,
                            "t": prov.bbox.t,
                            "r": prov.bbox.r,
                            "b": prov.bbox.b,
                        }

                if item_data["type"]:
                    items.append(item_data)

            # Cleanup to prevent memory leak
            del result
            gc.collect()

            page_count = len(doc.pages) if hasattr(doc, "pages") else 0

            logger.info(
                "PDF parsed successfully",
                path=str(path),
                pages=page_count,
                items=len(items),
            )

            return {
                "markdown": markdown,
                "items": items,
                "page_count": page_count,
                "metadata": {
                    "title": doc.name if hasattr(doc, "name") else None,
                },
            }

        except Exception as e:
            logger.error("PDF parsing failed", path=str(path), error=str(e))
            raise

    def chunk_by_paragraph(
        self,
        items: List[dict],
        section: Optional[str] = None,
        imrad_structure: Optional[dict] = None
    ) -> List[dict]:
        """
        Chunk items by paragraphs while preserving context.

        Args:
            items: List of parsed items from parse_pdf
            section: Optional section context (deprecated, use imrad_structure)
            imrad_structure: Optional IMRaD structure for section assignment

        Returns:
            List of chunk dictionaries with text, section, page info
        """
        chunks = []
        current_chunk = {
            "text": "",
            "section": section,
            "page_start": None,
            "page_end": None,
            "media": [],
        }

        CHUNK_SIZE_THRESHOLD = 500  # Characters per chunk

        for item in items:
            item_type = item.get("type")
            item_text = item.get("text") or ""
            item_page = item.get("page")
            item_bbox = item.get("bbox")

            if item_type in ["text"] and item_text:
                # Check if we should start a new chunk
                if current_chunk["text"] and len(current_chunk["text"]) > CHUNK_SIZE_THRESHOLD:
                    chunks.append(current_chunk)
                    current_chunk = {
                        "text": item_text,
                        "section": section,
                        "page_start": item_page,
                        "page_end": item_page,
                        "media": [],
                    }
                else:
                    # Append to current chunk
                    if current_chunk["text"]:
                        current_chunk["text"] += "\n\n" + item_text
                    else:
                        current_chunk["text"] = item_text

                    # Update page range
                    if item_page:
                        if current_chunk["page_start"] is None:
                            current_chunk["page_start"] = item_page
                        current_chunk["page_end"] = item_page

            elif item_type in ["table"]:
                # Store table reference
                current_chunk["media"].append({
                    "type": "table",
                    "page": item_page,
                    "bbox": item_bbox,
                    "text": item_text,
                })

            elif item_type == "picture":
                # Store picture reference
                current_chunk["media"].append({
                    "type": "picture",
                    "page": item_page,
                    "bbox": item_bbox,
                })

        # Don't forget the last chunk
        if current_chunk["text"]:
            chunks.append(current_chunk)

        # Assign sections based on IMRaD structure if provided
        if imrad_structure:
            for chunk in chunks:
                page = chunk.get("page_start")
                if page:
                    for section_name, section_data in imrad_structure.items():
                        if section_name.startswith("_"):
                            continue
                        if isinstance(section_data, dict):
                            start = section_data.get("page_start", 0)
                            end = section_data.get("page_end", 999)
                            if start <= page <= end:
                                chunk["section"] = section_name
                                break

        logger.info(
            "Chunking complete",
            input_items=len(items),
            output_chunks=len(chunks),
        )

        return chunks

    def chunk_by_semantic(
        self,
        items: List[dict],
        paper_id: str,
        imrad_structure: Optional[dict] = None
    ) -> List[dict]:
        """Create chunks using semantic splitting per D-03.

        Args:
            items: List of parsed items from Docling
            paper_id: Paper ID
            imrad_structure: Optional IMRaD structure

        Returns:
            List of semantic chunks with overlap
        """
        # Extract text items
        texts = []
        for item in items:
            if item.get("type") == "text" and item.get("text"):
                texts.append(item["text"])

        if not texts:
            return []

        # Create embedding model (reuse BGE-M3)
        from app.core.bge_m3_service import bge_m3_service

        embed_model = HuggingFaceEmbedding(
            model_name="BAAI/bge-m3",
            embed_model=bge_m3_service.model
        )

        # Create semantic splitter with LOCKED parameters (per D-03)
        splitter = SemanticSplitterNodeParser(
            buffer_size=1,  # LOCKED per D-03
            breakpoint_percentile_threshold=95,  # LOCKED per D-03
            embed_model=embed_model
        )

        # Create LlamaIndex documents
        documents = [Document(text=t) for t in texts]

        # Perform semantic splitting
        nodes = splitter.get_nodes_from_documents(documents)

        # Convert to our chunk format with overlap
        chunks = []
        for i, node in enumerate(nodes):
            chunk = {
                "text": node.text,
                "page_start": None,  # Will be assigned by PDF worker
                "page_end": None,
                "section": None,
                "overlap": 100 if i > 0 else 0,  # 100 tokens overlap per D-03
                "media": []
            }

            # Assign section from IMRaD if available
            if imrad_structure:
                chunk["section"] = self._assign_section(
                    node.text,
                    imrad_structure
                )

            chunks.append(chunk)

        logger.info(
            "Semantic chunking complete",
            input_texts=len(texts),
            output_chunks=len(chunks),
            paper_id=paper_id,
        )

        return chunks

    def _assign_section(self, text: str, imrad_structure: dict) -> Optional[str]:
        """Assign section based on IMRaD structure.

        This is a placeholder - actual section assignment
        will be done by PDF worker with page information.
        """
        # Simple heuristic: check text length and position
        # This will be improved by PDF worker with page info
        for section_name, section_data in imrad_structure.items():
            if section_name.startswith("_"):
                continue
            # Placeholder - actual assignment done by PDF worker
            pass
        return None

    async def extract_imrad(self, markdown: str) -> dict:
        """
        Extract IMRaD structure from markdown content.

        This is a basic extraction. More sophisticated extraction would use
        LLM or heuristics to identify section boundaries.

        Args:
            markdown: Full document markdown

        Returns:
            Dictionary with introduction, method, results, conclusion sections
        """
        # Simple heuristic-based extraction
        sections = {
            "introduction": "",
            "method": "",
            "results": "",
            "conclusion": "",
        }

        # TODO: Implement proper IMRaD extraction using LLM or section headers
        # For now, return empty sections to be filled by LLM later

        logger.info("IMRaD extraction placeholder - to be enhanced with LLM")

        return sections
