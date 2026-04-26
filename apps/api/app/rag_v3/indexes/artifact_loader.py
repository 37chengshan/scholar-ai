"""Load paper/section summary indexes from pre-computed artifact chunks.

Phase 1 RAPTOR-style approach: build lightweight in-memory summary index
from existing artifact JSON files (no re-parsing, no re-chunking).
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.rag_v3.indexes.paper_index import PaperSummaryIndex
from app.rag_v3.indexes.section_index import SectionSummaryIndex
from app.rag_v3.schemas import PaperSummaryArtifact, SectionSummaryArtifact

_ARTIFACT_ROOT_DEFAULT = Path(__file__).resolve().parents[6] / "artifacts" / "papers"


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _safe_str(v: Any) -> str:
    return str(v) if v is not None else ""


def _build_paper_summary(paper_id: str, parse_id: str, chunks: list[dict]) -> PaperSummaryArtifact:
    """Build a paper-level summary artifact from raw chunks."""
    now = datetime.now(timezone.utc).isoformat()

    title = ""
    abstract_parts: list[str] = []
    intro_parts: list[str] = []
    method_parts: list[str] = []
    exp_parts: list[str] = []
    result_parts: list[str] = []
    limitation_parts: list[str] = []
    table_captions: list[str] = []
    figure_captions: list[str] = []
    representative_ids: list[str] = []

    datasets: set[str] = set()
    metrics: set[str] = set()
    methods: set[str] = set()
    tasks: set[str] = set()

    for chunk in chunks:
        section = _safe_str(chunk.get("normalized_section_path") or chunk.get("section_path") or "").lower()
        content = _safe_str(chunk.get("content_data") or "")
        anchor = _safe_str(chunk.get("anchor_text") or "")
        ctype = _safe_str(chunk.get("content_type") or "text").lower()
        cid = _safe_str(chunk.get("source_chunk_id") or "")

        if not title and (section in ("", "abstract", "introduction") or chunk.get("page_num") == 1):
            lines = content.split("\n")
            for line in lines[:5]:
                line = line.strip()
                if 10 < len(line) < 200 and not line.startswith("arXiv"):
                    title = line
                    break

        if "abstract" in section:
            abstract_parts.append(anchor or content[:500])
            if cid:
                representative_ids.append(cid)
        elif "introduction" in section:
            intro_parts.append(anchor or content[:300])
        elif any(k in section for k in ("method", "approach", "model", "architecture", "system")):
            method_parts.append(anchor or content[:300])
        elif any(k in section for k in ("experiment", "evaluation", "result", "benchmark")):
            exp_parts.append(anchor or content[:300])
        elif any(k in section for k in ("ablation",)):
            result_parts.append(anchor or content[:300])
        elif any(k in section for k in ("limitation", "future")):
            limitation_parts.append(anchor or content[:300])

        if ctype == "table" and anchor:
            table_captions.append(anchor[:200])
        elif ctype in ("figure", "caption") and anchor:
            figure_captions.append(anchor[:200])

        # Extract metadata keywords (simple heuristic)
        meta = chunk.get("metadata") or {}
        if isinstance(meta, dict):
            for d in (meta.get("datasets") or []):
                datasets.add(_safe_str(d))
            for m in (meta.get("metrics") or []):
                metrics.add(_safe_str(m))
            for m in (meta.get("methods") or []):
                methods.add(_safe_str(m))

    paper_summary = " ".join(abstract_parts[:3]) or " ".join(intro_parts[:2])
    method_summary = " ".join(method_parts[:3])
    experiment_summary = " ".join(exp_parts[:3])
    result_summary = " ".join(result_parts[:2])
    limitation_summary = " ".join(limitation_parts[:2])

    return PaperSummaryArtifact(
        paper_id=paper_id,
        parse_id=parse_id,
        title=title[:300],
        abstract=" ".join(abstract_parts[:2])[:1000],
        paper_summary=paper_summary[:1500],
        method_summary=method_summary[:1000],
        experiment_summary=experiment_summary[:1000],
        result_summary=result_summary[:800],
        limitation_summary=limitation_summary[:800],
        datasets=sorted(datasets)[:20],
        metrics=sorted(metrics)[:20],
        methods=sorted(methods)[:20],
        tasks=sorted(tasks)[:20],
        table_captions=table_captions[:10],
        figure_captions=figure_captions[:10],
        representative_source_chunk_ids=representative_ids[:5],
        created_at=now,
    )


def _build_section_summaries(paper_id: str, parse_id: str, chunks: list[dict]) -> list[SectionSummaryArtifact]:
    """Group chunks by section and build section-level summaries."""
    now = datetime.now(timezone.utc).isoformat()
    section_chunks: dict[str, list[dict]] = defaultdict(list)
    for chunk in chunks:
        section = _safe_str(chunk.get("normalized_section_path") or chunk.get("section_path") or "unknown")
        section_chunks[section].append(chunk)

    results: list[SectionSummaryArtifact] = []
    for section_path, schunks in section_chunks.items():
        section_id = f"{paper_id}::{section_path}"
        anchors = [_safe_str(c.get("anchor_text") or "")[:200] for c in schunks if c.get("anchor_text")]
        section_summary = " ".join(anchors[:5]) or " ".join(
            _safe_str(c.get("content_data") or "")[:200] for c in schunks[:3]
        )
        source_chunk_ids = [_safe_str(c.get("source_chunk_id") or "") for c in schunks if c.get("source_chunk_id")]
        table_ids = [_safe_str(c.get("source_chunk_id") or "") for c in schunks if c.get("content_type") == "table"]
        figure_ids = [_safe_str(c.get("source_chunk_id") or "") for c in schunks if c.get("content_type") in ("figure", "caption")]

        # Extract simple key terms from section path
        key_terms = [t.strip() for t in section_path.replace("_", " ").replace("/", " ").split() if len(t) > 2]

        results.append(
            SectionSummaryArtifact(
                section_id=section_id,
                paper_id=paper_id,
                parse_id=parse_id,
                section_path=section_path,
                normalized_section_path=section_path,
                section_title=section_path.replace("_", " ").title(),
                section_summary=section_summary[:1200],
                key_terms=key_terms[:20],
                source_chunk_ids=source_chunk_ids[:50],
                table_ids=table_ids[:10],
                figure_ids=figure_ids[:10],
                created_at=now,
            )
        )
    return results


def build_indexes_from_artifacts(
    artifact_root: Path | None = None,
    stage: str = "raw",
    paper_ids: list[str] | None = None,
) -> tuple[PaperSummaryIndex, SectionSummaryIndex]:
    """Build paper and section indexes from artifact chunk files.

    Args:
        artifact_root: Path to artifacts/papers directory.
        stage: Chunk stage to use ('raw', 'rule', 'llm').
        paper_ids: If provided, only load these paper IDs.

    Returns:
        Tuple of (PaperSummaryIndex, SectionSummaryIndex).
    """
    root = artifact_root or _ARTIFACT_ROOT_DEFAULT
    paper_index = PaperSummaryIndex()
    section_index = SectionSummaryIndex()

    if not root.exists():
        return paper_index, section_index

    dirs = sorted(root.iterdir())
    for paper_dir in dirs:
        if not paper_dir.is_dir():
            continue
        pid = paper_dir.name
        if paper_ids and pid not in paper_ids:
            continue

        chunk_file = paper_dir / f"chunks_{stage}.json"
        if not chunk_file.exists():
            chunk_file = paper_dir / "chunks_raw.json"
        if not chunk_file.exists():
            continue

        try:
            chunks: list[dict] = _read_json(chunk_file)
            if not isinstance(chunks, list) or not chunks:
                continue

            parse_id = _safe_str(chunks[0].get("parse_id") or "")
            paper_summary = _build_paper_summary(pid, parse_id, chunks)
            paper_index.upsert(paper_summary)

            for section_art in _build_section_summaries(pid, parse_id, chunks):
                section_index.upsert(section_art)
        except Exception:
            continue

    return paper_index, section_index
