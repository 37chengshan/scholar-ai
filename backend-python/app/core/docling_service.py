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
from typing import Any, Dict, List, Optional

from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, InputFormat, PdfFormatOption
from docling_core.types.doc import TextItem, TableItem, PictureItem

# Semantic chunking imports (per D-03)
from llama_index.core.node_parser import SemanticSplitterNodeParser
from llama_index.core import Document
from app.core.embedding.llama_index_adapter import Qwen3VLLlamaIndexEmbedding

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
        items: List[Dict[str, Any]],
        paper_id: str,
        imrad_structure: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """Chunk text with semantic awareness and page tracking.

        Args:
            items: Parsed items from Docling
            paper_id: Paper UUID
            imrad_structure: IMRaD section info (optional)

        Returns:
            List of chunks with page tracking and section info
        """
        chunks = []
        
        for item in items:
            if item.get("type") != "text" or not item.get("text"):
                continue
            
            text = item["text"]
            page = item.get("page", 0)
            
            if len(text) < 50:
                continue
            
            section = self._assign_section(text, imrad_structure) if imrad_structure else ""
            
            chunks.append({
                "text": text,
                "page_start": page,
                "page_end": page,
                "section": section,
                "media": [],
                "has_equations": self._has_equations(text),
                "has_figures": "figure" in text.lower() or "table" in text.lower(),
            })
        
        merged = self._merge_small_chunks(chunks, target_size=200, min_size=50)
        
        logger.info(
            "Semantic chunking complete",
            input_items=len(items),
            initial_chunks=len(chunks),
            merged_chunks=len(merged),
            paper_id=paper_id,
        )
        
        return merged
    
    def _has_equations(self, text: str) -> bool:
        """Detect if text contains equations."""
        import re
        equation_patterns = [
            r'\$[^$]+\$',  # LaTeX inline math
            r'\$\$[^$]+\$\$',  # LaTeX display math
            r'\\[a-zA-Z]+\{',  # LaTeX commands
            r'[=+\-*/^]',  # Math operators
        ]
        return any(re.search(p, text) for p in equation_patterns)
    
    def _merge_small_chunks(
        self,
        chunks: List[Dict[str, Any]],
        target_size: int = 400,
        min_size: int = 100,
        max_size: int = 600
    ) -> List[Dict[str, Any]]:
        """Merge small chunks with fixed size strategy and overlap.
        
        RAG best practice (Pinecone/LlamaIndex):
        - target_size: 400 words (~512 tokens) - balanced precision and context
        - min_size: 100 words - minimum chunk to keep separate
        - max_size: 600 words - hard limit to prevent oversized chunks
        - Results in chunks of 300-500 words typically
        
        Args:
            chunks: List of initial chunks
            target_size: Target word count per chunk (default 400)
            min_size: Minimum chunk size to keep separate (default 100)
            max_size: Maximum chunk size - hard limit (default 600)
        
        Returns:
            List of merged chunks with controlled sizes
        """
        if not chunks:
            return []
        
        merged = []
        current_chunk = None
        
        for chunk in chunks:
            word_count = len(chunk["text"].split())
            
            if current_chunk is None:
                current_chunk = chunk.copy()
                current_chunk["word_count"] = word_count
            else:
                current_words = current_chunk["word_count"]
                new_total = current_words + word_count
                
                # Merge conditions:
                # 1. Current chunk < target_size AND new chunk < min_size
                # 2. AND total won't exceed max_size
                should_merge = (
                    current_words < target_size and 
                    word_count < min_size and
                    new_total <= max_size
                )
                
                if should_merge:
                    # Merge chunks
                    current_chunk["text"] += "\n\n" + chunk["text"]
                    current_chunk["word_count"] += word_count
                    current_chunk["page_end"] = chunk["page_end"]
                    if chunk.get("section"):
                        current_chunk["section"] = chunk["section"]
                else:
                    # Save current chunk and start new one
                    merged.append(current_chunk)
                    current_chunk = chunk.copy()
                    current_chunk["word_count"] = word_count
        
        # Don't forget the last chunk
        if current_chunk:
            merged.append(current_chunk)
        
        return merged

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
