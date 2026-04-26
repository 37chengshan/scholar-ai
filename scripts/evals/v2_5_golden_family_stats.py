#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Set

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.evals.v2_4_common import write_json, write_markdown

DEFAULT_GOLDEN = ROOT / "artifacts" / "benchmarks" / "v2_5" / "golden_queries_real_50.json"
DEFAULT_OUTPUT_DIR = ROOT / "artifacts" / "benchmarks" / "v2_5"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="v2.5 golden family stats")
    p.add_argument("--golden", default=str(DEFAULT_GOLDEN))
    p.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return p.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    payload = json.loads(Path(args.golden).read_text(encoding="utf-8"))
    queries: List[Dict[str, Any]] = payload.get("queries", []) if isinstance(payload, dict) else []

    by_family = Counter([str(q.get("query_family") or "") for q in queries])
    papers: Set[str] = set()
    chunks: Set[str] = set()
    content_types = Counter()
    abstain_count = 0

    for q in queries:
        if str(q.get("expected_answer_mode") or "") == "abstain":
            abstain_count += 1
        for pid in q.get("expected_paper_ids", []) or []:
            papers.add(str(pid))
        for sid in q.get("expected_source_chunk_ids", []) or []:
            chunks.add(str(sid))
        for ctype in q.get("expected_content_types", []) or []:
            content_types[str(ctype)] += 1

    report = {
        "total_queries": len(queries),
        "queries_by_family": dict(by_family),
        "papers_covered": len(papers),
        "chunks_covered": len(chunks),
        "content_types_covered": dict(content_types),
        "table_query_count": int(by_family.get("table", 0)),
        "figure_query_count": int(by_family.get("figure", 0)),
        "numeric_query_count": int(by_family.get("numeric", 0)),
        "compare_query_count": int(by_family.get("compare", 0)),
        "cross_paper_query_count": int(by_family.get("cross_paper", 0)),
        "hard_query_count": int(by_family.get("hard", 0)),
        "abstain_query_count": abstain_count,
        "status": "PASS",
    }

    write_json(out_dir / "golden_family_stats_50.json", report)
    lines = [
        f"- total_queries: {report['total_queries']}",
        f"- papers_covered: {report['papers_covered']}",
        f"- chunks_covered: {report['chunks_covered']}",
        f"- abstain_query_count: {report['abstain_query_count']}",
        "",
        "## Query Family Counts",
    ]
    for fam, cnt in sorted(by_family.items()):
        lines.append(f"- {fam}: {cnt}")

    lines.extend(["", "## Content Types Covered"])
    for ctype, cnt in sorted(content_types.items()):
        lines.append(f"- {ctype}: {cnt}")

    write_markdown(out_dir / "golden_family_stats_50.md", "v2.5 Golden Family Stats", lines)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
