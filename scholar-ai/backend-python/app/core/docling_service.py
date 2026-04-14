"""Docling PDF parser service with OCR support

Provides async wrapper around Docling for PDF parsing with:
- OCR enabled for scanned documents
- Multi-language support (en, zh)
- Structured content extraction (text, tables, formulas)
- Page number and bounding box tracking
- Memory-efficient processing
- Advanced chunking with overlap, semantic boundaries, and quality evaluation
- Configurable parser options (OCR, image/table extraction, limits)

Per Sprint 4 Task 1: Configurable Docling options with proper defaults.

Note: Models should be downloaded to ~/.cache/docling/models
"""

import asyncio
import gc
import os
import re
import io
import numpy as np
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field

from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, InputFormat, PdfFormatOption
from docling_core.types.doc import TextItem, TableItem, PictureItem

from app.utils.logger import logger


# Custom exceptions for parser errors
class FileTooLargeError(Exception):
    """Raised when file exceeds size limit."""

    pass


class ParseTimeoutError(Exception):
    """Raised when parsing exceeds timeout limit."""

    pass


class PageLimitError(Exception):
    """Raised when page count exceeds limit."""

    pass


@dataclass
class ParserConfig:
    """Docling parser configuration with sensible defaults.

    Per Sprint 4 Task 1: Configurable options for OCR and multimodal extraction.
    """

    # OCR settings
    do_ocr: bool = True  # Default enabled (was False)
    ocr_languages: List[str] = field(default_factory=lambda: ["en", "zh"])

    # Image/table extraction
    generate_picture_images: bool = True  # Default enabled (was False)
    generate_table_images: bool = True  # Default enabled (was False)

    # Safety limits
    max_num_pages: int = 100
    max_file_size_mb: int = 50
    timeout_seconds: int = 300

    @classmethod
    def from_settings(cls) -> "ParserConfig":
        """Load parser config from application settings."""
        from app.config import settings

        return cls(
            do_ocr=settings.PARSER_DO_OCR,
            ocr_languages=settings.PARSER_OCR_LANGUAGE.split(","),
            generate_picture_images=settings.PARSER_GENERATE_PICTURE_IMAGES,
            generate_table_images=settings.PARSER_GENERATE_TABLE_IMAGES,
            max_num_pages=settings.PARSER_MAX_PAGES,
            max_file_size_mb=settings.PARSER_MAX_FILE_SIZE_MB,
            timeout_seconds=settings.PARSER_TIMEOUT_SECONDS,
        )


class ChunkQualityReport:
    """Quality report for chunk evaluation."""

    def __init__(self, metrics: Dict[str, Any]):
        self.metrics = metrics
        self.score = self._calculate_score()

    def _calculate_score(self) -> float:
        """Calculate overall quality score (0-100)."""
        weights = {
            "avg_size_target_match": 0.3,
            "size_variance": 0.2,
            "boundary_quality": 0.25,
            "semantic_coherence": 0.25,
        }

        scores = {
            "avg_size_target_match": self._score_size_match(),
            "size_variance": self._score_variance(),
            "boundary_quality": self.metrics.get("boundary_quality", 0.7),
            "semantic_coherence": self.metrics.get("semantic_coherence", 0.8),
        }

        return sum(weights[k] * scores[k] for k in weights)

    def _score_size_match(self) -> float:
        """Score how well avg size matches target."""
        avg_size = self.metrics.get("avg_size", 400)
        target_size = self.metrics.get("target_size", 400)

        deviation = abs(avg_size - target_size) / target_size
        return max(0, 1 - deviation)

    def _score_variance(self) -> float:
        """Score size consistency (lower variance = better)."""
        variance = self.metrics.get("size_variance", 0)

        if variance < 100:
            return 1.0
        elif variance < 300:
            return 0.7
        elif variance < 500:
            return 0.4
        else:
            return 0.1

    def __repr__(self) -> str:
        return f"ChunkQualityReport(score={self.score:.1f}/100, avg_size={self.metrics['avg_size']:.0f} words)"


class DoclingParser:
    """PDF parser using Docling with OCR support and advanced chunking.

    Per Sprint 4 Task 1: Configurable options with defaults enabled.
    """

    def __init__(self, config: Optional[ParserConfig] = None):
        """Initialize Docling parser with configurable pipeline options.

        Args:
            config: ParserConfig instance (loads from settings if None)
        """
        self.config = config or ParserConfig.from_settings()

        model_path = Path.home() / ".cache" / "docling" / "models"
        if model_path.exists():
            os.environ["DOCLING_MODELS_PATH"] = str(model_path)
            logger.info("Using local Docling models", path=str(model_path))

        # Per Sprint 4 Task 1: Use configurable options (defaults now enabled)
        self.pipeline_options = PdfPipelineOptions(
            generate_picture_images=self.config.generate_picture_images,
            generate_table_images=self.config.generate_table_images,
            images_scale=1.0,
            do_ocr=self.config.do_ocr,  # Default is True now
        )

        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=self.pipeline_options,
                )
            }
        )

        logger.info(
            "DoclingParser initialized",
            do_ocr=self.config.do_ocr,
            generate_picture_images=self.config.generate_picture_images,
            generate_table_images=self.config.generate_table_images,
            max_file_size_mb=self.config.max_file_size_mb,
            timeout_seconds=self.config.timeout_seconds,
        )

    async def parse_pdf(self, pdf_path: str, force_ocr: bool = False) -> dict:
        """
        Parse PDF and return structured content.

        Args:
            pdf_path: Path to PDF file
            force_ocr: Override default OCR setting (for scanned PDFs)

        Returns:
            Dictionary with:
            - markdown: Full document as markdown
            - items: List of items with type, text, page, bbox
            - page_count: Total number of pages (unified field)
            - metadata: Document metadata

        Raises:
            FileTooLargeError: if file exceeds max_file_size_mb
            ParseTimeoutError: if parsing exceeds timeout_seconds

        Per Sprint 4:
        - Task 1: force_ocr override for scanned PDFs
        - Task 2: Unified 'page_count' field (not 'pages')
        - Task 3: File size and timeout limits
        """
        path = Path(pdf_path)

        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        # Task 3: Check file size before parsing
        file_size_mb = os.path.getsize(path) / (1024 * 1024)
        if file_size_mb > self.config.max_file_size_mb:
            raise FileTooLargeError(
                f"File size {file_size_mb:.1f}MB exceeds limit {self.config.max_file_size_mb}MB"
            )

        logger.info(
            "Starting PDF parsing",
            path=str(path),
            file_size_mb=file_size_mb,
            force_ocr=force_ocr,
        )

        try:
            # Task 1: Override OCR if force_ocr=True
            if force_ocr and not self.config.do_ocr:
                logger.info("Force OCR override for scanned PDF", path=str(path))
                # Recreate converter with OCR enabled
                override_options = PdfPipelineOptions(
                    generate_picture_images=self.config.generate_picture_images,
                    generate_table_images=self.config.generate_table_images,
                    images_scale=1.0,
                    do_ocr=True,  # Override
                )
                converter = DocumentConverter(
                    format_options={
                        InputFormat.PDF: PdfFormatOption(
                            pipeline_options=override_options,
                        )
                    }
                )
            else:
                converter = self.converter

            # Task 3: Parse with timeout protection
            result = await asyncio.wait_for(
                asyncio.to_thread(converter.convert, path),
                timeout=self.config.timeout_seconds,
            )
            doc = result.document

            markdown = doc.export_to_markdown()

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
                    item_data["text"] = None

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

            del result
            gc.collect()

            # Task 2: Unified field name 'page_count' (not 'pages')
            page_count = len(doc.pages) if hasattr(doc, "pages") else 0

            logger.info(
                "PDF parsed successfully",
                path=str(path),
                page_count=page_count,  # Unified field
                items=len(items),
            )

            return {
                "markdown": markdown,
                "items": items,
                "page_count": page_count,  # Task 2: Always use 'page_count'
                "metadata": {
                    "title": doc.name if hasattr(doc, "name") else None,
                },
            }

        except asyncio.TimeoutError:
            logger.error(
                "PDF parsing timeout",
                path=str(path),
                timeout_seconds=self.config.timeout_seconds,
            )
            raise ParseTimeoutError(
                f"Parsing exceeded timeout {self.config.timeout_seconds}s"
            )

        except Exception as e:
            logger.error("PDF parsing failed", path=str(path), error=str(e))
            raise

    def chunk_by_paragraph(
        self,
        items: List[dict],
        section: Optional[str] = None,
        imrad_structure: Optional[dict] = None,
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

        CHUNK_SIZE_THRESHOLD = 500

        for item in items:
            item_type = item.get("type")
            item_text = item.get("text") or ""
            item_page = item.get("page")
            item_bbox = item.get("bbox")

            if item_type in ["text"] and item_text:
                if (
                    current_chunk["text"]
                    and len(current_chunk["text"]) > CHUNK_SIZE_THRESHOLD
                ):
                    chunks.append(current_chunk)
                    current_chunk = {
                        "text": item_text,
                        "section": section,
                        "page_start": item_page,
                        "page_end": item_page,
                        "media": [],
                    }
                else:
                    if current_chunk["text"]:
                        current_chunk["text"] += "\n\n" + item_text
                    else:
                        current_chunk["text"] = item_text

                    if item_page:
                        if current_chunk["page_start"] is None:
                            current_chunk["page_start"] = item_page
                        current_chunk["page_end"] = item_page

            elif item_type in ["table"]:
                current_chunk["media"].append(
                    {
                        "type": "table",
                        "page": item_page,
                        "bbox": item_bbox,
                        "text": item_text,
                    }
                )

            elif item_type == "picture":
                current_chunk["media"].append(
                    {
                        "type": "picture",
                        "page": item_page,
                        "bbox": item_bbox,
                    }
                )

        if current_chunk["text"]:
            chunks.append(current_chunk)

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
        imrad_structure: Optional[Dict] = None,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Chunk text with semantic awareness, overlap, and quality optimization.

        Per D-03: Advanced semantic chunking with:
        - Config-driven chunk size (default 500 words)
        - Overlap mechanism (default 100 words)
        - Semantic boundary protection
        - IMRaD-adaptive chunk sizes
        - Quality evaluation

        Args:
            items: Parsed items from Docling
            paper_id: Paper UUID
            imrad_structure: IMRaD section info (optional)
            chunk_size: Override config chunk size (optional)
            chunk_overlap: Override config overlap (optional)

        Returns:
            List of chunks with page tracking, section info, and overlap tracking
        """
        from app.config import settings

        chunk_size = chunk_size or settings.CHUNK_SIZE
        chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

        chunks = []

        for item in items:
            if item.get("type") != "text" or not item.get("text"):
                continue

            text = item["text"]
            page = item.get("page", 0)

            word_count = len(text.split())
            if word_count < 1:
                continue

            section = (
                self._assign_section(text, imrad_structure) if imrad_structure else ""
            )

            has_equations = self._has_equations(text)
            has_figures = "figure" in text.lower() or "table" in text.lower()
            has_special_boundaries = self._detect_special_boundaries(text)

            adaptive_size = chunk_size
            if imrad_structure and section:
                adaptive_size = self._adaptive_chunk_size_by_section(
                    section, chunk_size
                )

            chunks.append(
                {
                    "text": text,
                    "page_start": page,
                    "page_end": page,
                    "section": section,
                    "media": [],
                    "has_equations": has_equations,
                    "has_figures": has_figures,
                    "has_special_boundaries": has_special_boundaries,
                    "adaptive_size": adaptive_size,
                    "word_count": word_count,
                }
            )

        merged = self._merge_small_chunks_with_overlap(
            chunks,
            target_size=chunk_size,
            min_size=100,
            max_size=chunk_size + 100,
            overlap=chunk_overlap,
        )

        quality_report = self._evaluate_chunk_quality(
            merged, chunk_size, max_size=chunk_size + 100
        )

        logger.info(
            "Semantic chunking complete",
            input_items=len(items),
            initial_chunks=len(chunks),
            merged_chunks=len(merged),
            paper_id=paper_id,
            chunk_size=chunk_size,
            overlap=chunk_overlap,
            avg_chunk_words=sum(len(c["text"].split()) for c in merged) / len(merged)
            if merged
            else 0,
            quality_score=quality_report.score,
        )

        return merged

    def _has_equations(self, text: str) -> bool:
        """Detect if text contains equations."""
        equation_patterns = [
            r"\$[^$]+\$",  # LaTeX inline math
            r"\$\$[^$]+\$\$",  # LaTeX display math
            r"\\[a-zA-Z]+\{",  # LaTeX commands
            r"[=+\-*/^]",  # Math operators
        ]
        return any(re.search(p, text) for p in equation_patterns)

    def _detect_special_boundaries(self, text: str) -> bool:
        """Detect special content that should not be split.

        Protects:
        - LaTeX formula blocks
        - Code blocks
        - Algorithm pseudocode
        - Table/Figure references
        """
        special_patterns = [
            r"\$\$[^$]+\$\$",  # LaTeX formula blocks
            r"```[^`]+```",  # Code blocks
            r"Algorithm \d+",  # Algorithm pseudocode
            r"Table \d+",  # Table references
            r"Figure \d+",  # Figure references
            r"\\begin{[^}]+}",  # LaTeX begin blocks
            r"\\end{[^}]+}",  # LaTeX end blocks
        ]
        return any(re.search(p, text) for p in special_patterns)

    def _adaptive_chunk_size_by_section(self, section: str, base_size: int) -> int:
        """Adjust chunk size based on IMRaD section characteristics.

        Academic papers have different needs per section:
        - Introduction: Needs more context (background + motivation)
        - Methods: Medium size (step-by-step procedures)
        - Results: Medium size (data + observations)
        - Discussion: Larger size (complete arguments)
        - Conclusion: Smaller size (concise summary)

        Args:
            section: IMRaD section name
            base_size: Base chunk size from config

        Returns:
            Adaptive chunk size for the section
        """
        size_multiplier = {
            "introduction": 1.3,  # +30% for background
            "methods": 1.0,  # Standard for procedures
            "results": 1.1,  # +10% for data
            "discussion": 1.4,  # +40% for arguments
            "conclusion": 0.8,  # -20% for concise summary
            "abstract": 0.9,  # -10% for summary
        }

        multiplier = size_multiplier.get(section.lower(), 1.0)
        return int(base_size * multiplier)

    def _merge_small_chunks_with_overlap(
        self,
        chunks: List[Dict[str, Any]],
        target_size: int = 400,
        min_size: int = 100,
        max_size: int = 600,
        overlap: int = 100,
    ) -> List[Dict[str, Any]]:
        """Merge small chunks with overlap mechanism for better context preservation.

        RAG best practice (Pinecone/LlamaIndex):
        - target_size: 400-500 words (~512-640 tokens) - balanced precision and context
        - min_size: 100 words - minimum chunk to keep separate
        - max_size: 600-700 words - hard limit
        - overlap: 100 words - prevents boundary content loss

        Args:
            chunks: List of initial chunks
            target_size: Target word count per chunk
            min_size: Minimum chunk size to keep separate
            max_size: Maximum chunk size - hard limit
            overlap: Number of words to overlap between chunks

        Returns:
            List of merged chunks with overlap tracking
        """
        if not chunks:
            return []

        merged = []
        current_chunk = None

        for i, chunk in enumerate(chunks):
            word_count = len(chunk["text"].split())
            adaptive_size = chunk.get("adaptive_size", target_size)

            if current_chunk is None:
                current_chunk = chunk.copy()
                current_chunk["word_count"] = word_count
                current_chunk["overlap"] = 0
            else:
                current_words = current_chunk["word_count"]
                new_total = current_words + word_count

                should_merge = (
                    current_words < adaptive_size
                    and word_count < min_size * 0.5
                    and new_total <= max_size
                    and not current_chunk.get("has_special_boundaries")
                    and not chunk.get("has_special_boundaries")
                )

                if should_merge:
                    current_chunk["text"] += "\n\n" + chunk["text"]
                    current_chunk["word_count"] += word_count
                    current_chunk["page_end"] = chunk["page_end"]
                    if chunk.get("section"):
                        current_chunk["section"] = chunk["section"]
                else:
                    merged.append(current_chunk)
                    current_chunk = chunk.copy()
                    current_chunk["word_count"] = word_count
                    current_chunk["overlap"] = 0

        if current_chunk:
            merged.append(current_chunk)

        for i in range(1, len(merged)):
            if overlap > 0 and i > 0:
                prev_text = merged[i - 1]["text"]
                prev_words = prev_text.split()

                overlap_words = (
                    prev_words[-overlap:] if len(prev_words) >= overlap else prev_words
                )
                overlap_text = " ".join(overlap_words)

                merged[i]["text"] = overlap_text + "\n\n" + merged[i]["text"]
                merged[i]["overlap"] = overlap

        for chunk in merged:
            chunk["word_count"] = len(chunk["text"].split())
            if "adaptive_size" in chunk:
                del chunk["adaptive_size"]

        return merged

    def _evaluate_chunk_quality(
        self, chunks: List[Dict[str, Any]], target_size: int = 400, max_size: int = 600
    ) -> ChunkQualityReport:
        """Evaluate chunk splitting quality.

        Metrics:
        - Average size vs target size
        - Size variance (consistency)
        - Boundary quality (special content preservation)
        - Semantic coherence (estimated)

        Args:
            chunks: List of merged chunks
            target_size: Target chunk size
            max_size: Maximum chunk size for boundary quality check

        Returns:
            ChunkQualityReport with quality score
        """
        if not chunks:
            return ChunkQualityReport(
                {
                    "avg_size": 0,
                    "target_size": target_size,
                    "size_variance": 0,
                    "boundary_quality": 1.0,
                    "semantic_coherence": 1.0,
                }
            )

        sizes = [chunk["word_count"] for chunk in chunks]

        avg_size = np.mean(sizes)
        size_variance = np.var(sizes) if len(sizes) > 1 else 0

        boundary_quality = 1.0
        for chunk in chunks:
            if chunk.get("has_special_boundaries"):
                chunk_size = chunk["word_count"]
                if chunk_size > max_size * 1.2:
                    boundary_quality -= 0.1

        boundary_quality = max(0, boundary_quality)

        semantic_coherence = 0.8
        section_chunks = {}
        for chunk in chunks:
            section = chunk.get("section", "unknown")
            if section not in section_chunks:
                section_chunks[section] = []
            section_chunks[section].append(chunk)

        for section, section_chunk_list in section_chunks.items():
            if len(section_chunk_list) > 1:
                avg_section_size = np.mean(
                    [c["word_count"] for c in section_chunk_list]
                )
                target_section_size = self._adaptive_chunk_size_by_section(
                    section, target_size
                )

                deviation = (
                    abs(avg_section_size - target_section_size) / target_section_size
                )
                if deviation < 0.2:
                    semantic_coherence += 0.05

        semantic_coherence = min(1.0, semantic_coherence)

        metrics = {
            "avg_size": avg_size,
            "target_size": target_size,
            "size_variance": size_variance,
            "boundary_quality": boundary_quality,
            "semantic_coherence": semantic_coherence,
            "chunk_count": len(chunks),
            "min_size": min(sizes),
            "max_size": max(sizes),
        }

        return ChunkQualityReport(metrics)

    def _assign_section(self, text: str, imrad_structure: dict) -> str:
        """Assign section based on IMRaD structure.

        This is a placeholder - actual section assignment
        will be done by PDF worker with page information.

        Returns empty string instead of None to prevent None-related errors.
        """
        for section_name, section_data in imrad_structure.items():
            if section_name.startswith("_"):
                continue
            pass
        return ""  # Fix: Return empty string instead of None

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
        sections = {
            "introduction": "",
            "method": "",
            "results": "",
            "conclusion": "",
        }

        logger.info("IMRaD extraction placeholder - to be enhanced with LLM")

        return sections
