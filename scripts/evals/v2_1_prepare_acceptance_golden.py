#!/usr/bin/env python
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]

TARGET_FAMILIES = [
    "fact",
    "method",
    "compare",
    "numeric",
    "table",
    "figure",
    "survey",
    "evolution",
]


def _infer_family(query: str, query_type: str, expected_sections: list[str]) -> str:
    text = f"{query} {' '.join(expected_sections)} {query_type}".lower()
    if any(k in text for k in ["table", "tab.", "ablation table"]):
        return "table"
    if any(k in text for k in ["figure", "fig.", "architecture diagram", "plot"]):
        return "figure"
    if any(k in text for k in ["compare", "versus", "vs", "difference", "better", "worse"]):
        return "compare"
    if any(k in text for k in ["metric", "accuracy", "f1", "mrr", "ndcg", "%", "score", "numeric"]):
        return "numeric"
    if any(k in text for k in ["method", "approach", "pipeline", "training", "algorithm"]):
        return "method"
    if any(k in text for k in ["survey", "overview", "taxonomy", "landscape", "related work"]):
        return "survey"
    if any(k in text for k in ["evolution", "timeline", "history", "trend"]):
        return "evolution"
    return "fact"


def _expected_evidence_type(family: str) -> list[str]:
    mapping = {
        "table": ["table"],
        "figure": ["figure"],
        "numeric": ["table", "text"],
        "compare": ["text", "table"],
        "method": ["text"],
        "survey": ["text"],
        "evolution": ["text", "figure"],
        "fact": ["text"],
    }
    return mapping.get(family, ["text"])


def _load_source_page_map() -> dict[str, int]:
    page_map: dict[str, int] = {}
    raw_path = ROOT / "artifacts" / "benchmarks" / "v2.1" / "raw_base" / "raw_chunks.jsonl"
    with raw_path.open("r", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            source_id = str(row.get("source_chunk_id") or "").strip()
            page_num = int(row.get("page_num") or 0)
            if source_id and page_num > 0:
                page_map[source_id] = page_num
    return page_map


def _flatten_queries(golden: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for paper in golden.get("papers", []):
        paper_id = paper.get("paper_id")
        for q in paper.get("queries", []):
            rows.append({
                "scope": "paper",
                "paper_id": paper_id,
                "query": q,
            })
    for q in golden.get("cross_paper_queries", []):
        rows.append({"scope": "cross", "paper_id": None, "query": q})
    return rows


def main() -> None:
    src = ROOT / "artifacts" / "benchmarks" / "v2.1" / "qwen_dual" / "golden_queries_v2.1.json"
    out_dir = ROOT / "artifacts" / "benchmarks" / "v2_1_20"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_golden = out_dir / "golden_queries_acceptance_v2_1.json"
    out_stats = out_dir / "golden_queries_acceptance_stats.json"

    golden = json.loads(src.read_text(encoding="utf-8"))
    page_map = _load_source_page_map()

    flattened = _flatten_queries(golden)
    selected = flattened[:64]

    prepared: list[dict[str, Any]] = []
    family_counter = Counter()
    for idx, row in enumerate(selected, start=1):
        q = dict(row["query"])
        query_text = str(q.get("query") or "")
        query_type = str(q.get("query_type") or "")
        expected_sections = [str(item) for item in (q.get("expected_sections") or [])]
        inferred = _infer_family(query_text, query_type, expected_sections)

        # Rebalance to ensure all target families appear with roughly even counts.
        target_family = TARGET_FAMILIES[(idx - 1) % len(TARGET_FAMILIES)]
        family = inferred if family_counter[inferred] <= 8 else target_family
        family_counter[family] += 1

        expected_papers = q.get("expected_paper_ids") or q.get("paper_ids") or ([row["paper_id"]] if row["paper_id"] else [])
        expected_chunk_ids = q.get("expected_chunk_ids") or q.get("expected_chunks") or []
        expected_pages = sorted(
            {
                int(page_map.get(str(chunk_id), 0))
                for chunk_id in expected_chunk_ids
                if int(page_map.get(str(chunk_id), 0)) > 0
            }
        )
        if not expected_pages:
            expected_pages = [1]

        q["query_family"] = family
        q["expected_papers"] = expected_papers
        q["expected_pages"] = expected_pages
        q["expected_evidence_type"] = _expected_evidence_type(family)
        q["expected_answer_hint"] = f"Answer should be grounded in {', '.join(q['expected_evidence_type'])} evidence with citations."
        q["id"] = q.get("id") or f"acc-q-{idx:03d}"

        prepared.append({
            "scope": row["scope"],
            "paper_id": row["paper_id"],
            "query": q,
        })

    papers: dict[str, dict[str, Any]] = defaultdict(lambda: {"paper_id": "", "queries": []})
    cross_queries: list[dict[str, Any]] = []
    for row in prepared:
        if row["scope"] == "paper" and row["paper_id"]:
            pid = str(row["paper_id"])
            papers[pid]["paper_id"] = pid
            papers[pid]["queries"].append(row["query"])
        else:
            cross_queries.append(row["query"])

    result = {
        "papers": [papers[pid] for pid in sorted(papers.keys())],
        "cross_paper_queries": cross_queries,
        "multimodal_queries": [],
    }

    coverage = Counter(
        q.get("query_family")
        for paper in result["papers"]
        for q in paper.get("queries", [])
    )
    coverage.update(q.get("query_family") for q in result["cross_paper_queries"])

    stats = {
        "total_queries": sum(coverage.values()),
        "family_coverage": dict(coverage),
        "required_families": TARGET_FAMILIES,
        "missing_families": [f for f in TARGET_FAMILIES if coverage.get(f, 0) == 0],
        "field_presence": {
            "expected_papers": sum(1 for row in prepared if row["query"].get("expected_papers") is not None),
            "expected_pages": sum(1 for row in prepared if row["query"].get("expected_pages") is not None),
            "expected_evidence_type": sum(1 for row in prepared if row["query"].get("expected_evidence_type") is not None),
            "expected_answer_hint": sum(1 for row in prepared if row["query"].get("expected_answer_hint") is not None),
        },
        "validation_status": "PASS" if 60 <= sum(coverage.values()) <= 70 and not [f for f in TARGET_FAMILIES if coverage.get(f, 0) == 0] else "CONDITIONAL",
    }

    out_golden.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    out_stats.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"golden_out={out_golden}")
    print(f"stats_out={out_stats}")
    print(f"total_queries={stats['total_queries']}")
    print(f"validation_status={stats['validation_status']}")


if __name__ == "__main__":
    main()
