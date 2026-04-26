"""Batch storage manager for PDF pipeline.

Consolidates all storage operations into single transaction per paper:
- PostgreSQL: paper metadata, IMRaD, notes
- Milvus: text chunks, images, tables (batched)
- Neo4j: chunk nodes, section nodes

Per D-06: Batch storage reduces database round trips.
"""

import json
import re
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional

import asyncpg

from app.workers.pipeline_context import PipelineContext
from app.contracts.chunk_artifact import (
    ChunkArtifact,
    ChunkStage,
    build_chunk_artifacts,
    derive_stage_chunk_artifacts,
)
from app.core.milvus_service import get_milvus_service, calculate_chunk_quality
from app.core.neo4j_service import Neo4jService
from app.core.notes_generator import NotesGenerator
from app.core.docling_service import DoclingParser
from app.core.section_normalizer import (
    normalize_section_path,
    section_leaf,
    section_parent_path,
    serialize_section_path,
)
from app.core.qwen3vl_service import get_qwen3vl_service
from app.core.contextual_chunk_builder import enrich_chunk, build_section_summary_text
from app.utils.logger import logger


class StorageManager:
    """Batch storage manager for consolidated database writes."""

    EMBEDDING_DIM = 2048  # Qwen3VL dimension
    MIN_CHUNK_QUALITY = 0.25
    MAX_INDEXED_TITLE_LEN = 240

    def __init__(
        self,
        db_pool: asyncpg.Pool,
        milvus_service=None,
        neo4j_service=None,
        notes_generator=None,
    ):
        """Initialize storage manager.

        Args:
            db_pool: PostgreSQL connection pool
            milvus_service: Milvus service (optional, uses singleton if None)
            neo4j_service: Neo4j service (optional, uses singleton if None)
            notes_generator: Notes generator (optional, uses singleton if None)
        """
        self.db_pool = db_pool
        self.milvus = milvus_service or get_milvus_service()
        self.neo4j = neo4j_service or Neo4jService()
        self.notes_generator = notes_generator or NotesGenerator()
        self.parser = DoclingParser()

        # Get or create Qwen3VL service. Keep lazy-loading to avoid startup crash;
        # actual hard validation happens during vector stage.
        self.qwen3vl_service = get_qwen3vl_service()

    @staticmethod
    def _sanitize_text(value: Optional[str]) -> Optional[str]:
        """Remove NUL bytes that PostgreSQL UTF-8 text columns reject."""
        if value is None:
            return None
        if not isinstance(value, str):
            value = str(value)
        if "\x00" in value:
            return value.replace("\x00", "")
        return value

    @classmethod
    def _sanitize_obj(cls, value: Any) -> Any:
        """Recursively sanitize strings in nested objects for DB persistence."""
        if isinstance(value, str):
            return cls._sanitize_text(value)
        if isinstance(value, list):
            return [cls._sanitize_obj(v) for v in value]
        if isinstance(value, dict):
            return {k: cls._sanitize_obj(v) for k, v in value.items()}
        return value

    @classmethod
    def _normalize_title(cls, value: Optional[str]) -> Optional[str]:
        """Normalize parser title output to a compact, index-safe value."""
        text = cls._sanitize_text(value)
        if not text:
            return None

        first_non_empty_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
        normalized = re.sub(r"\s+", " ", first_non_empty_line).strip()

        if not normalized:
            return None

        if len(normalized) > cls.MAX_INDEXED_TITLE_LEN:
            normalized = normalized[: cls.MAX_INDEXED_TITLE_LEN].rstrip()

        return normalized or None

    async def _ensure_unique_title_for_user(
        self,
        conn: asyncpg.Connection,
        user_id: str,
        paper_id: str,
        candidate: str,
    ) -> str:
        """Resolve title collisions for unique_user_title before UPDATE.

        Metadata extraction can produce the same canonical title across multiple
        imports. Ensure `(userId, title)` stays unique without failing the whole
        processing pipeline.
        """

        probe_sql = (
            'SELECT id FROM papers WHERE "userId" = $1 AND title = $2 AND id <> $3 LIMIT 1'
        )

        existing_id = await conn.fetchval(probe_sql, user_id, candidate, paper_id)
        if not isinstance(existing_id, str):
            return candidate

        for idx in range(2, 100):
            next_candidate = f"{candidate} (v{idx})"
            next_existing = await conn.fetchval(probe_sql, user_id, next_candidate, paper_id)
            if not isinstance(next_existing, str):
                return next_candidate

        return f"{candidate} ({paper_id[:8]})"

    async def _generate_notes_with_retry(
        self,
        paper_metadata: Dict[str, Any],
        imrad_structure: Dict[str, Any],
        max_retries: int = 2,
        timeout_seconds: int = 90,
    ) -> str:
        """Generate notes with timeout and bounded retries for worker stability."""
        last_error: Optional[Exception] = None

        for attempt in range(max_retries + 1):
            try:
                return await asyncio.wait_for(
                    self.notes_generator.generate_notes(
                        paper_metadata=paper_metadata,
                        imrad_structure=imrad_structure,
                    ),
                    timeout=timeout_seconds,
                )
            except Exception as e:
                last_error = e
                logger.warning(
                    "Reading notes generation attempt failed",
                    attempt=attempt + 1,
                    max_attempts=max_retries + 1,
                    error=str(e),
                )
                if attempt < max_retries:
                    await asyncio.sleep(min(2 ** attempt, 4))

        raise RuntimeError("Failed to generate reading notes after retries") from last_error

    @staticmethod
    def _build_evidence_metadata(
        chunk: Dict[str, Any],
        chunk_text: str,
        parse_metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build evidence-level metadata for downstream retrieval/verifier stages."""
        section = chunk.get("section") or chunk.get("section_path") or ""
        page_num = chunk.get("page_num")
        snippet = chunk_text.replace("\n", " ").strip()
        anchor_text = str(chunk.get("anchor_text") or snippet[:200])
        raw_section_path = str(chunk.get("raw_section_path") or section)
        normalized_section_path = str(
            chunk.get("normalized_section_path")
            or serialize_section_path(normalize_section_path(raw_section_path))
        )
        normalized_section_leaf = str(
            chunk.get("normalized_section_leaf") or section_leaf(normalize_section_path(raw_section_path))
        )
        section_level = int(chunk.get("section_level") or len(normalize_section_path(raw_section_path)))
        parent_section_path = str(
            chunk.get("parent_section_path")
            or section_parent_path(normalize_section_path(raw_section_path))
        )
        char_start = chunk.get("char_start")
        char_end = chunk.get("char_end")
        chunk_id = str(chunk.get("chunk_id") or "")
        source_chunk_id = str(chunk.get("source_chunk_id") or "")

        figure_match = re.search(r"\b(?:figure|fig\.)\s*(\d+)\b", snippet, re.IGNORECASE)
        table_match = re.search(r"\btable\s*(\d+)\b", snippet, re.IGNORECASE)
        figure_id = f"figure-{figure_match.group(1)}" if figure_match else None
        table_id = f"table-{table_match.group(1)}" if table_match else None

        caption_match = re.search(
            r"\b(?:figure|fig\.|table)\s*\d+\s*[:.-]\s*([^\n.]{1,120})",
            chunk_text,
            re.IGNORECASE,
        )
        caption = caption_match.group(1).strip() if caption_match else None

        source_span = {
            "start_char": 0,
            "end_char": min(len(chunk_text), 200),
        }

        nearby_explanation = ""
        lower_snippet = snippet.lower()
        if "figure" in lower_snippet or "fig." in lower_snippet:
            nearby_explanation = "contains_figure_reference"
        elif "table" in lower_snippet:
            nearby_explanation = "contains_table_reference"

        return {
            "evidence_version": "v1",
            "content_subtype": "paragraph",
            "section_path": section,
            "raw_section_path": raw_section_path,
            "normalized_section_path": normalized_section_path,
            "normalized_section_leaf": normalized_section_leaf,
            "section_level": section_level,
            "parent_section_path": parent_section_path,
            "anchor_text": anchor_text,
            "source_span": source_span,
            "chunk_id": chunk_id,
            "source_chunk_id": source_chunk_id,
            "char_start": char_start,
            "char_end": char_end,
            "figure_id": figure_id,
            "table_id": table_id,
            "caption": caption,
            "nearby_explanation": nearby_explanation,
            "parse_mode": parse_metadata.get("parse_mode"),
            "ocr_used": parse_metadata.get("ocr_used"),
            "parse_warnings": parse_metadata.get("parse_warnings", []),
            "chunk_strategy": parse_metadata.get("chunk_strategy", {}),
            "page_num": page_num,
        }

    @staticmethod
    def _build_text_record_from_chunk_artifact(
        *,
        chunk_artifact: Dict[str, Any],
        paper_id: str,
        user_id: str,
        chunk_text: str,
        raw_text: str,
        embedding: List[float],
        section: str,
        raw_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "chunk_id": chunk_artifact.get("chunk_id", ""),
            "source_chunk_id": chunk_artifact.get("source_chunk_id", ""),
            "stage": chunk_artifact.get("stage", ChunkStage.RAW.value),
            "parent_source_chunk_id": chunk_artifact.get("parent_source_chunk_id"),
            "paper_id": paper_id,
            "user_id": user_id,
            "content_type": "text",
            "page_num": chunk_artifact.get("page_num") if chunk_artifact.get("page_num") is not None else 0,
            "char_start": chunk_artifact.get("char_start"),
            "char_end": chunk_artifact.get("char_end"),
            "anchor_text": chunk_artifact.get("anchor_text"),
            "raw_section_path": chunk_artifact.get("section_path", ""),
            "normalized_section_path": chunk_artifact.get("normalized_section_path", ""),
            "normalized_section_leaf": chunk_artifact.get("section_leaf", ""),
            "section_level": len(normalize_section_path(str(chunk_artifact.get("section_path") or ""))),
            "parent_section_path": section_parent_path(
                normalize_section_path(str(chunk_artifact.get("section_path") or ""))
            ),
            "section": section,
            "text": raw_text,
            "content_data": chunk_text[:8000],
            "context_window": chunk_artifact.get("context_window", ""),
            "subsection": chunk_artifact.get("section_leaf", ""),
            "raw_data": raw_data,
            "embedding": embedding,
        }

    @staticmethod
    def _paper_artifact_dir(paper_id: str) -> Path:
        path = Path("artifacts") / "papers" / paper_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def _write_chunk_artifacts(
        cls,
        *,
        paper_id: str,
        stage: ChunkStage,
        chunks: List[ChunkArtifact],
    ) -> None:
        artifact_path = cls._paper_artifact_dir(paper_id) / f"chunks_{stage.value}.json"
        payload = [item.model_dump(mode="json") for item in chunks]
        artifact_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    async def store(self, ctx: PipelineContext) -> PipelineContext:
        """Store all extraction results in batch.

        Single transaction for:
        1. Paper metadata and IMRaD (PostgreSQL)
        2. Reading notes (PostgreSQL)
        3. All content vectors (Milvus batched)
        4. Graph nodes (Neo4j)

        Args:
            ctx: Pipeline context with extraction results

        Returns:
            Updated context
        """
        logger.info("Starting batch storage", task_id=ctx.task_id)

        async with self.db_pool.acquire() as conn:
            # 1. Update paper metadata and IMRaD
            await self._store_paper_metadata(conn, ctx)

            # 2. Generate and store reading notes
            await self._store_notes(conn, ctx)

        # 3. Store all content vectors in Milvus (batched)
        chunk_ids = await self._store_vectors(ctx)

        # 4. Store graph nodes in Neo4j
        await self._store_graph_nodes(ctx, chunk_ids)

        logger.info(
            "Batch storage complete", task_id=ctx.task_id, paper_id=ctx.paper_id
        )

        return ctx

    async def _store_paper_metadata(
        self, conn: asyncpg.Connection, ctx: PipelineContext
    ) -> None:
        """Update paper with metadata and IMRaD.

        Per D-04: Always update title from extracted metadata when available.
        Filename-based title should be replaced with extracted title from PDF.
        """
        metadata = self._sanitize_obj(ctx.metadata or {})
        imrad = self._sanitize_obj(ctx.imrad or {})
        markdown = self._sanitize_text((ctx.parse_result or {}).get("markdown", ""))

        # Extract title from metadata, convert empty strings to None
        extracted_title = self._normalize_title(metadata.get("title"))

        if extracted_title:
            extracted_title = await self._ensure_unique_title_for_user(
                conn=conn,
                user_id=ctx.user_id,
                paper_id=ctx.paper_id,
                candidate=extracted_title,
            )

        # Per D-04: Use extracted title if available (overwrites filename-based title)
        # Only fallback to existing title if extraction truly failed
        title_update_clause = "title = $4" if extracted_title else "title = title"

        await conn.execute(
            f"""UPDATE papers
               SET content = $1,
                   "pageCount" = $2,
                   status = 'processing',
                   "imradJson" = $3,
                   {title_update_clause},
                   authors = COALESCE(NULLIF($5::text[], '{{}}'), authors),
                   abstract = COALESCE(NULLIF($6, ''), abstract),
                   doi = COALESCE(NULLIF($7, ''), doi),
                   keywords = COALESCE(NULLIF($8::text[], '{{}}'), keywords),
                   "updatedAt" = NOW()
               WHERE id = $9""",
            markdown,
            (ctx.parse_result or {}).get("page_count", 0),
            json.dumps(imrad),
            extracted_title,  # $4 - only used if title_update_clause is "title = $4"
            metadata.get("authors", []),
            self._sanitize_text(metadata.get("abstract")),
            self._sanitize_text(metadata.get("doi")),
            metadata.get("keywords", []),
            ctx.paper_id,
        )

        logger.debug(
            "Paper metadata stored", task_id=ctx.task_id, paper_id=ctx.paper_id
        )

    async def _store_notes(
        self, conn: asyncpg.Connection, ctx: PipelineContext
    ) -> None:
        """Generate and store reading notes."""
        try:
            paper_metadata = {
                "title": ctx.metadata.get("title", "Unknown")
                if ctx.metadata
                else "Unknown",
                "authors": ctx.metadata.get("authors", []) if ctx.metadata else [],
                "year": ctx.metadata.get("year", "") if ctx.metadata else "",
                "venue": ctx.metadata.get("venue", "") if ctx.metadata else "",
            }

            notes = await self._generate_notes_with_retry(
                paper_metadata=paper_metadata,
                imrad_structure=ctx.imrad or {},
            )

            notes = self._sanitize_text(notes)
            if notes:
                await conn.execute(
                    """UPDATE papers
                       SET reading_notes = $1,
                           notes_version = notes_version + 1,
                           "updatedAt" = NOW()
                       WHERE id = $2""",
                    notes,
                    ctx.paper_id,
                )

                ctx.notes = notes

                logger.debug(
                    "Reading notes stored", task_id=ctx.task_id, notes_length=len(notes)
                )

        except Exception as e:
            logger.warning(
                "Failed to generate notes, continuing without",
                task_id=ctx.task_id,
                error=str(e),
            )

    async def _store_vectors(self, ctx: PipelineContext) -> List[int]:
        """Store all content vectors in Milvus (batched).

        Per D-06, D-27: Single batched insert for text, images, tables.
        """
        all_contents = []
        text_contents = []
        parse_metadata = (ctx.parse_result or {}).get("metadata", {})
        parse_artifact = ctx.parse_artifact or {}
        parse_items = parse_artifact.get("items")
        parse_id = str(parse_artifact.get("parse_id") or "")

        if not parse_id:
            logger.warning(
                "Missing ParseArtifact parse_id, skipping vector storage",
                task_id=ctx.task_id,
            )
            return []

        if not isinstance(parse_items, list):
            logger.warning(
                "Missing parse_result.items, skipping vector storage",
                task_id=ctx.task_id,
            )
            if ctx.parse_result is None:
                ctx.parse_result = {}
            if not isinstance(ctx.parse_result.get("metadata"), dict):
                ctx.parse_result["metadata"] = {}
            ctx.parse_result["metadata"]["quality_gate"] = {
                "threshold": self.MIN_CHUNK_QUALITY,
                "input_chunks": 0,
                "indexed_chunks": 0,
                "skipped_chunks": 0,
                "image_records": len(ctx.image_results or []),
                "table_records": len(ctx.table_results or []),
                "skip_reason": "missing_parse_items",
            }
            return []

        # 1. Generate text chunks from parsed content
        chunks = self.parser.chunk_by_semantic(
            parse_items,
            paper_id=ctx.paper_id,
            imrad_structure=ctx.imrad,
        )

        raw_chunk_artifacts = build_chunk_artifacts(
            parse_id=parse_id,
            paper_id=ctx.paper_id,
            semantic_chunks=chunks,
        )
        rule_chunk_artifacts = derive_stage_chunk_artifacts(raw_chunk_artifacts, ChunkStage.RULE)
        llm_chunk_artifacts = derive_stage_chunk_artifacts(raw_chunk_artifacts, ChunkStage.LLM)

        self._write_chunk_artifacts(
            paper_id=ctx.paper_id,
            stage=ChunkStage.RAW,
            chunks=raw_chunk_artifacts,
        )
        self._write_chunk_artifacts(
            paper_id=ctx.paper_id,
            stage=ChunkStage.RULE,
            chunks=rule_chunk_artifacts,
        )
        self._write_chunk_artifacts(
            paper_id=ctx.paper_id,
            stage=ChunkStage.LLM,
            chunks=llm_chunk_artifacts,
        )

        ctx.chunk_artifacts = {
            "raw": [chunk.model_dump(mode="json") for chunk in raw_chunk_artifacts],
            "rule": [chunk.model_dump(mode="json") for chunk in rule_chunk_artifacts],
            "llm": [chunk.model_dump(mode="json") for chunk in llm_chunk_artifacts],
        }

        # Assign sections based on IMRaD
        chunk_texts = []
        for chunk in raw_chunk_artifacts:
            page = chunk.page_num
            if page and ctx.imrad:
                for section_name, section_data in ctx.imrad.items():
                    if section_name.startswith("_"):
                        continue
                    if isinstance(section_data, dict):
                        start = section_data.get("page_start", 0)
                        end = section_data.get("page_end", 999)
                        if start and end and start <= page <= end:
                            chunk.section_path = section_name or ""
                            normalized_path_tokens = normalize_section_path(chunk.section_path)
                            chunk.normalized_section_path = serialize_section_path(normalized_path_tokens)
                            chunk.section_leaf = section_leaf(normalized_path_tokens)
                            break

            chunk_text = self._sanitize_text(chunk.content_data) or ""
            if not chunk_text or not chunk_text.strip():
                chunk_text = "NULL"

            # Iteration 2: build contextual chunk text for richer embedding
            paper_title = (ctx.metadata or {}).get("title") if ctx.metadata else None
            enriched = enrich_chunk(
                chunk={
                    "text": chunk.content_data,
                    "section": chunk.section_path,
                    "page_start": chunk.page_num,
                    "anchor_text": chunk.anchor_text,
                },
                paper_title=paper_title,
                all_page_items=parse_items,
                chunk_index=None,  # window expansion done at section level below
                window_size=1,
            )
            contextual_text = self._sanitize_text(enriched.get("content_data") or chunk_text) or chunk_text
            chunk_texts.append(contextual_text)
            # Store raw text for quality scoring / BM25
            chunk.content_data = chunk_text
            chunk.warnings = list(chunk.warnings)
            context_window = str(enriched.get("context_window", ""))
            if context_window:
                chunk.warnings.append("context_window_applied")

        # Batch generate embeddings (much faster than one-by-one)
        logger.info(
            "Generating embeddings in batch",
            task_id=ctx.task_id,
            chunk_count=len(chunk_texts),
        )

        # CRITICAL: Ensure model is loaded on GPU before encoding
        if not self.qwen3vl_service.is_loaded():
            logger.warning("Model not loaded, loading now...")
            self.qwen3vl_service.load_model()

        # Verify GPU usage
        logger.info(
            f"Embedding model status - Loaded: {self.qwen3vl_service.is_loaded()}, Device: {self.qwen3vl_service.get_device()}"
        )

        # Generate embeddings in smaller batches to avoid GPU memory overflow
        # MPS on Mac has limited GPU memory allocation
        BATCH_SIZE = 8
        embeddings = []

        try:
            for i in range(0, len(chunk_texts), BATCH_SIZE):
                batch = chunk_texts[i : i + BATCH_SIZE]
                batch_embeddings = self.qwen3vl_service.encode_text(batch)
                embeddings.extend(batch_embeddings)

                # Clear GPU cache after each batch
                import torch

                if torch.backends.mps.is_available():
                    torch.mps.empty_cache()

            logger.info(
                "Embeddings generated", task_id=ctx.task_id, count=len(embeddings)
            )
        except Exception as e:
            logger.error(
                "Failed to generate batch embeddings", task_id=ctx.task_id, error=str(e)
            )
            raise RuntimeError("Qwen embedding failed during batch generation") from e

        if len(embeddings) != len(chunk_texts):
            logger.error(
                "Embedding count mismatch",
                task_id=ctx.task_id,
                chunk_count=len(chunk_texts),
                embedding_count=len(embeddings),
            )
            raise RuntimeError(
                f"Qwen embedding count mismatch: chunks={len(chunk_texts)}, embeddings={len(embeddings)}"
            )

        # Add chunks with embeddings
        skipped_low_quality = 0
        for i, chunk in enumerate(raw_chunk_artifacts):
            chunk_text = chunk_texts[i]
            embedding = embeddings[i]

            section = chunk.section_leaf or chunk.section_path or ""
            raw_text = chunk.content_data or chunk_text

            quality_score = calculate_chunk_quality(
                {
                    "text": raw_text,
                    "section": section,
                    "has_equations": False,
                    "has_figures": False,
                }
            )

            # PR7 quality gate: keep low-quality chunks out of main index.
            if quality_score < self.MIN_CHUNK_QUALITY:
                skipped_low_quality += 1
                continue

            raw_data = self._build_evidence_metadata(chunk.model_dump(mode="json"), raw_text, parse_metadata)

            text_record = self._build_text_record_from_chunk_artifact(
                chunk_artifact=chunk.model_dump(mode="json"),
                paper_id=ctx.paper_id,
                user_id=ctx.user_id,
                chunk_text=chunk_text,
                raw_text=raw_text,
                embedding=embedding,
                section=section,
                raw_data=raw_data,
            )
            text_contents.append(text_record)
            all_contents.append(text_record)

        quality_gate = {
            "threshold": self.MIN_CHUNK_QUALITY,
            "input_chunks": len(raw_chunk_artifacts),
            "indexed_chunks": len(text_contents),
            "skipped_chunks": skipped_low_quality,
            "image_records": len(ctx.image_results or []),
            "table_records": len(ctx.table_results or []),
        }

        if ctx.parse_result is not None:
            if "metadata" not in ctx.parse_result:
                ctx.parse_result["metadata"] = {}
            ctx.parse_result["metadata"]["quality_gate"] = quality_gate

        # 2. Add images
        if ctx.image_results:
            all_contents.extend(ctx.image_results)

        # 3. Add tables
        if ctx.table_results:
            all_contents.extend(ctx.table_results)

        # 4. Batch insert to Milvus
        if all_contents:
            chunk_ids = self.milvus.insert_contents_batched(all_contents)

            logger.info(
                "Vectors stored in Milvus",
                task_id=ctx.task_id,
                total=len(all_contents),
                chunks=len(raw_chunk_artifacts),
                indexed_chunks=len(text_contents),
                skipped_low_quality=skipped_low_quality,
                images=len(ctx.image_results or []),
                tables=len(ctx.table_results or []),
            )

            # 5. Iteration 2: build and store section-level summary index
            await self._store_summary_index(ctx, text_contents)

            ctx.chunk_results = text_contents
            # Keep text chunk ids for graph linking, but preserve ids for image/table-only inserts.
            if text_contents:
                return chunk_ids[: len(text_contents)]
            return chunk_ids

        return []

    async def _store_summary_index(
        self,
        ctx: PipelineContext,
        text_contents: List[Dict[str, Any]],
    ) -> None:
        """Build section-level summary index entries from text chunks (Iteration 2).

        Groups chunks by their section label, concatenates them into a summary
        document, and embeds + stores each summary in the paper_summaries collection.
        """
        if not text_contents:
            return

        paper_title = (ctx.metadata or {}).get("title") if ctx.metadata else None

        # Group chunks by section
        section_groups: Dict[str, List[Dict[str, Any]]] = {}
        for rec in text_contents:
            key = rec.get("section") or rec.get("normalized_section_path") or "unknown"
            section_groups.setdefault(key, []).append(rec)

        summary_entries: List[Dict[str, Any]] = []
        summary_texts: List[str] = []

        for section_name, section_chunks in section_groups.items():
            # Skip trivially short sections
            combined_len = sum(len(c.get("text", "")) for c in section_chunks)
            if combined_len < 100:
                continue

            summary_text = build_section_summary_text(
                section_name=section_name,
                chunks=section_chunks,
                paper_title=paper_title,
            )
            summary_texts.append(summary_text)
            summary_entries.append({
                "paper_id": ctx.paper_id,
                "user_id": ctx.user_id,
                "summary_type": "section_summary",
                "section_name": section_name,
                "content_data": summary_text,
            })

        # Also add a paper-level summary using all chunks combined
        if text_contents:
            all_text = " ".join(
                (c.get("text") or "")[:300] for c in text_contents[:30]
            )
            paper_summary_text = (
                f"[Paper Summary: {paper_title or 'unknown'}]\n{all_text}"
            )
            summary_texts.append(paper_summary_text)
            summary_entries.append({
                "paper_id": ctx.paper_id,
                "user_id": ctx.user_id,
                "summary_type": "paper_summary",
                "section_name": "_paper",
                "content_data": paper_summary_text,
            })

        if not summary_texts:
            return

        try:
            # Embed summaries in batches
            BATCH_SIZE = 8
            all_embeddings = []
            for i in range(0, len(summary_texts), BATCH_SIZE):
                batch = summary_texts[i:i + BATCH_SIZE]
                batch_embs = self.qwen3vl_service.encode_text(batch)
                all_embeddings.extend(batch_embs)

            for entry, emb in zip(summary_entries, all_embeddings):
                entry["embedding"] = emb

            self.milvus.insert_summaries_batched(summary_entries)
            logger.info(
                "Summary index stored",
                task_id=ctx.task_id,
                sections=len(summary_entries),
            )
        except Exception as exc:
            # Summary index failure is non-critical — degrade gracefully
            logger.warning(
                "Summary index storage failed, continuing",
                task_id=ctx.task_id,
                error=str(exc),
            )

    async def _store_graph_nodes(
        self, ctx: PipelineContext, chunk_ids: List[int]
    ) -> None:
        """Store chunk and section nodes in Neo4j."""
        if not chunk_ids or not (ctx.chunk_results or []):
            return

        try:
            # Create chunk nodes
            chunks_with_ids = [
                {"id": cid, **chunk}
                for chunk, cid in zip((ctx.chunk_results or [])[: len(chunk_ids)], chunk_ids)
            ]

            await self.neo4j.create_chunk_nodes(ctx.paper_id, chunks_with_ids)

            # Create section nodes
            section_data = {
                k: v
                for k, v in (ctx.imrad or {}).items()
                if not k.startswith("_") and isinstance(v, dict)
            }

            if section_data:
                await self.neo4j.create_section_nodes(ctx.paper_id, section_data)

            # Create paper node
            metadata = ctx.metadata or {}
            await self.neo4j.create_paper_node(
                paper_id=ctx.paper_id,
                title=metadata.get("title", "Untitled"),
                authors=metadata.get("authors", []),
                year=metadata.get("year"),
            )

            logger.debug(
                "Graph nodes stored", task_id=ctx.task_id, chunks=len(chunks_with_ids)
            )

        except Exception as e:
            logger.warning(
                "Neo4j storage failed, continuing", task_id=ctx.task_id, error=str(e)
            )


# Singleton
_storage_manager: Optional[StorageManager] = None


def get_storage_manager(db_pool: asyncpg.Pool = None) -> StorageManager:
    """Get or create StorageManager singleton.

    Args:
        db_pool: PostgreSQL connection pool (required on first call)

    Returns:
        StorageManager instance
    """
    global _storage_manager
    if _storage_manager is None and db_pool:
        _storage_manager = StorageManager(db_pool)
    return _storage_manager
