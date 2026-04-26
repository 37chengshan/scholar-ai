#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from pymilvus import Collection, connections

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.evals.v2_4_common import (
    DEFAULT_ARTIFACT_ROOT,
    collect_paper_artifacts,
    read_json,
    source_chunk_set,
    stage_collection_name,
)

DEFAULT_OUTPUT = ROOT / "artifacts" / "benchmarks" / "v2_5" / "golden_queries_real_50.json"

NUMERIC_PATTERN = re.compile(r"\b\d+(?:\.\d+)?\s*(?:%|kpc|km|dex|sigma|ms|hz|ghz|mhz)?\b", re.IGNORECASE)
METHOD_KEYWORDS = ("method", "approach", "pipeline", "framework", "model", "algorithm", "we propose")
COMPARE_KEYWORDS = ("compared", "compare", "versus", "while", "whereas", "better", "worse")

FAMILIES = ["fact", "method", "table", "figure", "numeric", "compare", "cross_paper", "hard"]
MIN_REQUIRED = {
    "fact": 20,
    "method": 10,
    "table": 8,
    "figure": 8,
    "numeric": 8,
    "compare": 8,
    "cross_paper": 8,
    "hard": 8,
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="v2.5 generate real golden queries")
    p.add_argument("--artifact-root", default=str(DEFAULT_ARTIFACT_ROOT))
    p.add_argument("--collection-profile", default="api_flash_v2_4")
    p.add_argument("--target-paper-count", type=int, default=50)
    p.add_argument("--target-query-count", type=int, default=80)
    p.add_argument("--collection-suffix", default="v2_4")
    p.add_argument("--output", default=str(DEFAULT_OUTPUT))
    p.add_argument("--milvus-host", default="localhost")
    p.add_argument("--milvus-port", type=int, default=19530)
    return p.parse_args()


def _snippet(text: str, size: int = 140) -> str:
    t = " ".join((text or "").split())
    return t[:size]


def _pick_chunk(chunks: List[Dict[str, Any]], predicate) -> Optional[Dict[str, Any]]:
    for chunk in chunks:
        if predicate(chunk):
            return chunk
    return None


def _chunk_text(chunk: Dict[str, Any]) -> str:
    return f"{chunk.get('content_data') or ''} {chunk.get('anchor_text') or ''}".strip()


def _has_numeric(chunk: Dict[str, Any]) -> bool:
    return bool(NUMERIC_PATTERN.search(_chunk_text(chunk)))


def _has_method(chunk: Dict[str, Any]) -> bool:
    text = _chunk_text(chunk).lower()
    return any(k in text for k in METHOD_KEYWORDS)


def _has_compare(chunk: Dict[str, Any]) -> bool:
    text = _chunk_text(chunk).lower()
    return any(k in text for k in COMPARE_KEYWORDS)


def _section(chunk: Dict[str, Any]) -> str:
    return str(chunk.get("normalized_section_path") or chunk.get("section_path") or "body")


def _query(
    *,
    query_id: str,
    text: str,
    family: str,
    expected_answer_mode: str,
    anchors: List[Dict[str, Any]],
    difficulty: str,
    notes: str,
) -> Dict[str, Any]:
    expected_paper_ids = sorted({str(a["paper_id"]) for a in anchors if str(a.get("paper_id") or "")})
    expected_source_chunk_ids = [str(a["source_chunk_id"]) for a in anchors if str(a.get("source_chunk_id") or "")]
    expected_content_types = sorted({str(a.get("content_type") or "text") for a in anchors if str(a.get("content_type") or "")})
    expected_sections = sorted({str(a.get("section") or "body") for a in anchors if str(a.get("section") or "")})

    return {
        "query_id": query_id,
        "query": text,
        "query_family": family,
        "expected_answer_mode": expected_answer_mode,
        "expected_paper_ids": expected_paper_ids,
        "expected_source_chunk_ids": expected_source_chunk_ids,
        "expected_content_types": expected_content_types or ["text"],
        "expected_sections": expected_sections or ["body"],
        "evidence_anchors": anchors,
        "golden_source": "chunk_artifact",
        "difficulty": difficulty,
        "notes": notes,
    }


def _anchor(chunk: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "paper_id": str(chunk.get("paper_id") or ""),
        "source_chunk_id": str(chunk.get("source_chunk_id") or ""),
        "page_num": int(chunk.get("page_num") or 0),
        "content_type": str(chunk.get("content_type") or "text"),
        "anchor_text": _snippet(str(chunk.get("anchor_text") or chunk.get("content_data") or ""), 220),
        "section": _section(chunk),
    }


def _collection_source_ids(suffix: str, host: str, port: int) -> Set[str]:
    connections.connect(alias="v25_generate", host=host, port=port)
    all_ids: Set[str] = set()
    for stage in ["raw", "rule", "llm"]:
        name = stage_collection_name(stage, suffix)
        col = Collection(name, using="v25_generate")
        col.load()
        rows = col.query(expr="id >= 0", output_fields=["source_chunk_id"], limit=16384)
        all_ids |= {str(r.get("source_chunk_id") or "") for r in rows if str(r.get("source_chunk_id") or "")}
    return all_ids


def main() -> int:
    args = parse_args()

    artifacts = collect_paper_artifacts(Path(args.artifact_root), limit_papers=args.target_paper_count)
    paper_chunks: Dict[str, List[Dict[str, Any]]] = {}
    for art in artifacts:
        raw = read_json(art.chunks_raw_path)
        paper_chunks[art.paper_id] = raw

    # Hard gate: ensure all anchor candidates are present in current v2.4 collections.
    collection_ids = _collection_source_ids(args.collection_suffix, args.milvus_host, args.milvus_port)

    queries: List[Dict[str, Any]] = []
    query_index = 1

    extra_family_budget = (
        MIN_REQUIRED["table"]
        + MIN_REQUIRED["figure"]
        + MIN_REQUIRED["numeric"]
        + MIN_REQUIRED["compare"]
        + MIN_REQUIRED["cross_paper"]
        + MIN_REQUIRED["hard"]
    )
    effective_target_query_count = max(args.target_query_count, args.target_paper_count + extra_family_budget)

    def next_qid() -> str:
        nonlocal query_index
        qid = f"real-{query_index:03d}"
        query_index += 1
        return qid

    # 1) Baseline per-paper: at least one fact/method.
    sorted_papers = sorted(paper_chunks.keys())
    for idx, pid in enumerate(sorted_papers):
        chunks = paper_chunks[pid]
        if not chunks:
            continue
        method_chunk = _pick_chunk(chunks, _has_method)
        fact_chunk = chunks[0]
        use_method = (idx % 2 == 0) and method_chunk is not None
        chosen = method_chunk if use_method else fact_chunk
        family = "method" if use_method else "fact"
        anchor = _anchor(chosen)
        if anchor["source_chunk_id"] not in collection_ids:
            continue
        prompt = (
            f"What method is described in paper {pid} and what evidence supports it?"
            if family == "method"
            else f"What is one key finding stated in paper {pid}?"
        )
        queries.append(
            _query(
                query_id=next_qid(),
                text=prompt,
                family=family,
                expected_answer_mode="full",
                anchors=[anchor],
                difficulty="easy",
                notes=f"generated_from_{family}_chunk",
            )
        )

    # 2) Add family-focused queries until target count.
    numeric_pool: List[Tuple[str, Dict[str, Any]]] = []
    compare_pool: List[Tuple[str, Dict[str, Any]]] = []
    hard_pool: List[Tuple[str, Dict[str, Any]]] = []
    table_pool: List[Tuple[str, Dict[str, Any]]] = []
    figure_pool: List[Tuple[str, Dict[str, Any]]] = []

    for pid, chunks in paper_chunks.items():
        for c in chunks:
            sid = str(c.get("source_chunk_id") or "")
            if not sid or sid not in collection_ids:
                continue
            text = _chunk_text(c)
            ctype = str(c.get("content_type") or "")
            if _has_numeric(c):
                numeric_pool.append((pid, c))
            if _has_compare(c):
                compare_pool.append((pid, c))
            if len(text) >= 600:
                hard_pool.append((pid, c))
            if ctype == "table" or "table" in text.lower():
                table_pool.append((pid, c))
            if ctype in {"figure", "caption", "page"} or "figure" in text.lower() or "fig." in text.lower():
                figure_pool.append((pid, c))

    def add_from_pool(pool: List[Tuple[str, Dict[str, Any]]], family: str, needed: int, prompt_builder, difficulty: str) -> None:
        nonlocal queries
        seen_sid = {
            sid
            for q in queries
            if q.get("query_family") == family
            for sid in q.get("expected_source_chunk_ids", [])
        }
        used_papers: Set[str] = set()
        added = 0
        for pid, chunk in pool:
            if pid in used_papers:
                continue
            sid = str(chunk.get("source_chunk_id") or "")
            if sid in seen_sid:
                continue
            a = _anchor(chunk)
            q = _query(
                query_id=next_qid(),
                text=prompt_builder(pid),
                family=family,
                expected_answer_mode="full",
                anchors=[a],
                difficulty=difficulty,
                notes=f"generated_from_{family}_pool",
            )
            queries.append(q)
            seen_sid.add(sid)
            used_papers.add(pid)
            added += 1
            if added >= needed or len(queries) >= effective_target_query_count:
                break

    add_from_pool(numeric_pool, "numeric", MIN_REQUIRED["numeric"], lambda pid: f"In paper {pid}, what numeric metrics are reported and what do they indicate?", "medium")
    add_from_pool(compare_pool, "compare", MIN_REQUIRED["compare"], lambda pid: f"Within paper {pid}, what comparison is made and what is the conclusion?", "medium")
    add_from_pool(hard_pool, "hard", MIN_REQUIRED["hard"], lambda pid: f"For paper {pid}, synthesize the key constraint and result with evidence.", "hard")

    # cross_paper queries from numeric pairs.
    pair_count = 0
    paper_anchor_for_cross: List[Tuple[str, Dict[str, Any]]] = []
    for pid in sorted_papers:
        chunks = paper_chunks.get(pid, [])
        c = _pick_chunk(chunks, _has_numeric) or (chunks[0] if chunks else None)
        if c is None:
            continue
        paper_anchor_for_cross.append((pid, c))

    for i in range(0, len(paper_anchor_for_cross) - 1, 2):
        pid1, c1 = paper_anchor_for_cross[i]
        pid2, c2 = paper_anchor_for_cross[i + 1]
        if pid1 == pid2 or pid1 > pid2:
            continue
        a1 = _anchor(c1)
        a2 = _anchor(c2)
        if not a1["source_chunk_id"] or not a2["source_chunk_id"]:
            continue
        queries.append(
            _query(
                query_id=next_qid(),
                text=f"Compare the reported quantitative findings between paper {pid1} and paper {pid2}.",
                family="cross_paper",
                expected_answer_mode="partial",
                anchors=[a1, a2],
                difficulty="hard",
                notes="generated_from_cross_paper_numeric_pair",
            )
        )
        pair_count += 1
        if pair_count >= MIN_REQUIRED["cross_paper"] or len(queries) >= effective_target_query_count:
            break

    # table/figure families are only generated when real evidence exists.
    table_added = 0
    table_seen_papers: Set[str] = set()
    for pid, chunk in table_pool:
        if pid in table_seen_papers:
            continue
        queries.append(
            _query(
                query_id=next_qid(),
                text=f"From paper {pid}, what does the referenced table show?",
                family="table",
                expected_answer_mode="full",
                anchors=[_anchor(chunk)],
                difficulty="medium",
                notes="generated_from_table_evidence",
            )
        )
        table_seen_papers.add(pid)
        table_added += 1
        if table_added >= MIN_REQUIRED["table"]:
            break

    figure_added = 0
    figure_seen_papers: Set[str] = set()
    for pid, chunk in figure_pool:
        if pid in figure_seen_papers:
            continue
        queries.append(
            _query(
                query_id=next_qid(),
                text=f"From paper {pid}, what is described by the referenced figure context?",
                family="figure",
                expected_answer_mode="full",
                anchors=[_anchor(chunk)],
                difficulty="medium",
                notes="generated_from_figure_evidence",
            )
        )
        figure_seen_papers.add(pid)
        figure_added += 1
        if figure_added >= MIN_REQUIRED["figure"]:
            break

    # Backfill fact/method if still below target.
    backfill_idx = 0
    while len(queries) < effective_target_query_count and sorted_papers:
        pid = sorted_papers[backfill_idx % len(sorted_papers)]
        chunks = paper_chunks[pid]
        if not chunks:
            backfill_idx += 1
            continue
        c = chunks[backfill_idx % len(chunks)]
        a = _anchor(c)
        if a["source_chunk_id"] not in collection_ids:
            backfill_idx += 1
            continue
        fam = "fact" if backfill_idx % 2 == 0 else "method"
        qtext = f"What evidence-backed {('finding' if fam == 'fact' else 'method detail')} appears in paper {pid}?"
        queries.append(
            _query(
                query_id=next_qid(),
                text=qtext,
                family=fam,
                expected_answer_mode="full",
                anchors=[a],
                difficulty="easy",
                notes="backfill_to_target_count",
            )
        )
        backfill_idx += 1

    # Deduplicate query_id and query text conservatively.
    dedup: List[Dict[str, Any]] = []
    seen_qid: Set[str] = set()
    seen_text: Set[str] = set()
    for q in queries:
        key = q["query"].strip().lower()
        if q["query_id"] in seen_qid or key in seen_text:
            continue
        seen_qid.add(q["query_id"])
        seen_text.add(key)
        dedup.append(q)

    queries = dedup[: effective_target_query_count]
    family_counts = Counter([q["query_family"] for q in queries])

    final_family_counts = Counter([q["query_family"] for q in queries])

    coverage = {
        "table_evidence_available": len(table_pool) > 0,
        "figure_evidence_available": len(figure_pool) > 0,
        "table_queries_generated": int(final_family_counts.get("table", 0)),
        "figure_queries_generated": int(final_family_counts.get("figure", 0)),
        "coverage_blocked_families": [
            fam
            for fam, ok in (
                ("table", len(table_pool) > 0),
                ("figure", len(figure_pool) > 0),
            )
            if not ok
        ],
    }

    payload = {
        "version": "v2_5_real_golden",
        "collection_profile": args.collection_profile,
        "target_paper_count": args.target_paper_count,
        "target_query_count": args.target_query_count,
        "query_count": len(queries),
        "families": dict(family_counts),
        "coverage": coverage,
        "queries": queries,
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    md_path = out_path.with_suffix(".md")
    lines = [
        "# v2.5 Real Golden Queries (50 papers)",
        "",
        f"- query_count: {payload['query_count']}",
        f"- target_query_count: {args.target_query_count}",
        f"- coverage_blocked_families: {', '.join(coverage['coverage_blocked_families']) or 'none'}",
        "",
        "## Family Counts",
    ]
    for fam in FAMILIES:
        lines.append(f"- {fam}: {family_counts.get(fam, 0)}")
    lines.extend(["", "## Notes", "- queries are generated only from real chunk evidence anchors"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
