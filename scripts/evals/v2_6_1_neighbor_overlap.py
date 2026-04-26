#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set

from scripts.evals.v2_6_1_common import DEFAULT_GOLDEN_PATH, ensure_output_dir, read_json, write_json_report, write_md_report


ROOT = Path(__file__).resolve().parents[2]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Step6.1 task G: neighbor overlap")
    p.add_argument("--golden-path", default=str(DEFAULT_GOLDEN_PATH))
    p.add_argument("--trace-path", default=str(ROOT / "artifacts" / "benchmarks" / "v2_6_1" / "retrieval_trace_16x3.jsonl"))
    return p.parse_args()


def _tokenize(text: str) -> Set[str]:
    return {t.lower() for t in text.split() if t.strip()}


def _artifact_stage_index(stage: str) -> Dict[str, Dict[str, Any]]:
    idx: Dict[str, Dict[str, Any]] = {}
    for paper_dir in sorted((ROOT / "artifacts" / "papers").iterdir()):
        if not paper_dir.is_dir():
            continue
        path = paper_dir / f"chunks_{stage}.json"
        if not path.exists():
            continue
        rows = read_json(path)
        for row in rows:
            sid = str(row.get("source_chunk_id") or "").strip()
            if sid:
                idx[sid] = row
    return idx


def _neighbors(stage_rows: Dict[str, Dict[str, Any]], paper_id: str) -> Dict[str, Set[str]]:
    rows = [
        r for r in stage_rows.values() if str(r.get("paper_id") or "") == paper_id and str(r.get("source_chunk_id") or "")
    ]
    rows.sort(key=lambda r: (int(r.get("page_num") or 0), int(r.get("char_start") or 0)))
    out: Dict[str, Set[str]] = {}
    for i, row in enumerate(rows):
        sid = str(row.get("source_chunk_id") or "")
        n: Set[str] = set()
        if i - 1 >= 0:
            n.add(str(rows[i - 1].get("source_chunk_id") or ""))
        if i + 1 < len(rows):
            n.add(str(rows[i + 1].get("source_chunk_id") or ""))
        out[sid] = {x for x in n if x}
    return out


def main() -> int:
    args = parse_args()
    out_dir = ensure_output_dir()
    golden = read_json(Path(args.golden_path))
    qmap = {str(q.get("query_id") or ""): q for q in (golden.get("queries") or [])}

    traces: List[Dict[str, Any]] = []
    with Path(args.trace_path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                traces.append(json.loads(line))

    stage_index = {stage: _artifact_stage_index(stage) for stage in ["raw", "rule", "llm"]}
    stage_neighbors: Dict[str, Dict[str, Set[str]]] = {}
    for stage in ["raw", "rule", "llm"]:
        nmap: Dict[str, Set[str]] = {}
        papers = {str(r.get("paper_id") or "") for r in stage_index[stage].values() if str(r.get("paper_id") or "")}
        for pid in papers:
            nmap.update(_neighbors(stage_index[stage], pid))
        stage_neighbors[stage] = nmap

    records: List[Dict[str, Any]] = []
    fam = defaultdict(list)

    for tr in traces:
        qid = str(tr.get("query_id") or "")
        stage = str(tr.get("stage") or "")
        q = qmap.get(qid, {})

        expected_sources = set(str(x) for x in (q.get("expected_source_chunk_ids") or []) if str(x))
        expected_papers = set(str(x) for x in (q.get("expected_paper_ids") or []) if str(x))
        expected_sections = set(str(x) for x in (q.get("expected_sections") or []) if str(x))
        expected_types = set(str(x) for x in (q.get("expected_content_types") or []) if str(x))

        got_sources = set(str(x) for x in (tr.get("retrieved_source_chunk_ids") or []) if str(x))
        got_papers = set(str(x) for x in (tr.get("retrieved_paper_ids") or []) if str(x))
        got_sections = set(str(x) for x in (tr.get("retrieved_sections") or []) if str(x))
        got_types = set(str(x) for x in (tr.get("retrieved_content_types") or []) if str(x))

        adjacent_pool: Set[str] = set()
        for sid in expected_sources:
            adjacent_pool |= stage_neighbors.get(stage, {}).get(sid, set())

        exact = bool(expected_sources & got_sources)
        same_paper = bool(expected_papers & got_papers)
        same_section = bool(expected_sections & got_sections)
        same_type = bool(expected_types & got_types)
        adjacent = bool(adjacent_pool & got_sources)

        expected_anchor = " ".join(str(a.get("anchor_text") or "") for a in (q.get("evidence_anchors") or []))
        retrieved_anchor = " ".join(str(x or "") for x in (tr.get("retrieved_anchor_texts") or []))
        overlap = bool(_tokenize(expected_anchor) & _tokenize(retrieved_anchor))

        rec = {
            "query_id": qid,
            "query_family": str(tr.get("query_family") or "unknown"),
            "stage": stage,
            "exact_chunk_hit": exact,
            "same_paper_hit": same_paper,
            "same_section_hit": same_section,
            "same_content_type_hit": same_type,
            "adjacent_chunk_hit": adjacent,
            "overlap_anchor_hit": overlap,
        }
        records.append(rec)
        fam[rec["query_family"]].append(rec)

    def _rate(items: List[Dict[str, Any]], key: str) -> float:
        if not items:
            return 0.0
        return round(sum(1 for i in items if i.get(key)) / len(items), 4)

    summary = {
        "total": len(records),
        "exact_chunk_hit_rate": _rate(records, "exact_chunk_hit"),
        "same_paper_hit_rate": _rate(records, "same_paper_hit"),
        "same_section_hit_rate": _rate(records, "same_section_hit"),
        "same_content_type_hit_rate": _rate(records, "same_content_type_hit"),
        "adjacent_chunk_hit_rate": _rate(records, "adjacent_chunk_hit"),
        "overlap_anchor_hit_rate": _rate(records, "overlap_anchor_hit"),
    }

    by_family = {
        family: {
            "count": len(items),
            "exact_chunk_hit_rate": _rate(items, "exact_chunk_hit"),
            "same_paper_hit_rate": _rate(items, "same_paper_hit"),
            "same_section_hit_rate": _rate(items, "same_section_hit"),
            "same_content_type_hit_rate": _rate(items, "same_content_type_hit"),
            "adjacent_chunk_hit_rate": _rate(items, "adjacent_chunk_hit"),
            "overlap_anchor_hit_rate": _rate(items, "overlap_anchor_hit"),
        }
        for family, items in sorted(fam.items())
    }

    report = {
        "status": "PASS",
        "summary": summary,
        "by_family": by_family,
        "records": records,
        "interpretation_hints": {
            "exact_0_paper_gt_0": "golden may be strict or chunk granularity mismatch",
            "exact_0_paper_0": "retrieval is off-target",
            "content_type_0": "table/figure/numeric routing risk",
            "adjacent_gt_0": "consider adding overlap_chunk_hit metric",
        },
    }

    json_path = out_dir / "neighbor_overlap_report.json"
    md_path = out_dir / "neighbor_overlap_report.md"
    write_json_report(json_path, report)

    lines = [
        f"- total: {summary['total']}",
        f"- exact_chunk_hit_rate: {summary['exact_chunk_hit_rate']}",
        f"- same_paper_hit_rate: {summary['same_paper_hit_rate']}",
        f"- same_section_hit_rate: {summary['same_section_hit_rate']}",
        f"- same_content_type_hit_rate: {summary['same_content_type_hit_rate']}",
        f"- adjacent_chunk_hit_rate: {summary['adjacent_chunk_hit_rate']}",
        f"- overlap_anchor_hit_rate: {summary['overlap_anchor_hit_rate']}",
    ]
    write_md_report(md_path, "Step6.1 Neighbor Overlap Report", lines)
    print(json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
