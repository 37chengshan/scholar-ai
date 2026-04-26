#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Set

from pymilvus import Collection, connections

ROOT = Path(__file__).resolve().parents[2]
API_ROOT = ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.model_gateway import create_embedding_provider
from scripts.evals.v2_4_common import OFFICIAL_MODEL, OFFICIAL_PROVIDER, stage_collection_name, write_json, write_markdown

DEFAULT_GOLDEN = ROOT / "artifacts" / "benchmarks" / "v2_5" / "golden_queries_real_50.json"
DEFAULT_OUTPUT_DIR = ROOT / "artifacts" / "benchmarks" / "v2_5"
REQUIRED_FAMILIES = ["fact", "method", "table", "figure", "numeric", "compare", "cross_paper", "hard"]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="v2.5 real golden small smoke")
    p.add_argument("--golden", default=str(DEFAULT_GOLDEN))
    p.add_argument("--collection-suffix", default="v2_4")
    p.add_argument("--provider", default=OFFICIAL_PROVIDER)
    p.add_argument("--model", default=OFFICIAL_MODEL)
    p.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    p.add_argument("--milvus-host", default="localhost")
    p.add_argument("--milvus-port", type=int, default=19530)
    return p.parse_args()


def _pick_one_per_family(queries: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    picked: Dict[str, Dict[str, Any]] = {}
    for q in queries:
        fam = str(q.get("query_family") or "")
        if fam in REQUIRED_FAMILIES and fam not in picked:
            picked[fam] = q
    return picked


def main() -> int:
    args = parse_args()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    payload = json.loads(Path(args.golden).read_text(encoding="utf-8"))
    queries = payload.get("queries", []) if isinstance(payload, dict) else []
    selected = _pick_one_per_family(queries)
    missing_families = [f for f in REQUIRED_FAMILIES if f not in selected]

    report: Dict[str, Any] = {
        "golden_path": str(Path(args.golden)),
        "required_families": REQUIRED_FAMILIES,
        "selected_count": len(selected),
        "missing_families": missing_families,
        "family_results": {},
        "status": "BLOCKED",
        "error": None,
    }

    try:
        connections.connect(alias="v25_smoke", host=args.milvus_host, port=args.milvus_port)
        provider = create_embedding_provider(args.provider, args.model)

        # Build corpus id/paper map from raw stage only (alignment already enforced in v2.4).
        raw_col = Collection(stage_collection_name("raw", args.collection_suffix), using="v25_smoke")
        raw_col.load()
        rows = raw_col.query(expr="id >= 0", output_fields=["paper_id", "source_chunk_id"], limit=16384)
        corpus_papers: Set[str] = {str(r.get("paper_id") or "") for r in rows if str(r.get("paper_id") or "")}
        corpus_sources: Set[str] = {str(r.get("source_chunk_id") or "") for r in rows if str(r.get("source_chunk_id") or "")}

        for family, q in selected.items():
            expected_papers = [str(x) for x in q.get("expected_paper_ids", [])]
            expected_sources = [str(x) for x in q.get("expected_source_chunk_ids", [])]

            missing_expected_papers = [p for p in expected_papers if p not in corpus_papers]
            missing_expected_sources = [s for s in expected_sources if s not in corpus_sources]

            vec = provider.embed_texts([str(q.get("query") or "")])[0]
            stage_hits: Dict[str, int] = {}
            for stage in ["raw", "rule", "llm"]:
                name = stage_collection_name(stage, args.collection_suffix)
                col = Collection(name, using="v25_smoke")
                col.load()
                hits = col.search(
                    data=[vec],
                    anns_field="embedding",
                    param={"metric_type": "COSINE", "params": {"nprobe": 10}},
                    limit=3,
                    output_fields=["paper_id", "source_chunk_id"],
                )
                stage_hits[stage] = len(hits[0]) if hits else 0

            ok = not missing_expected_papers and not missing_expected_sources and all(v > 0 for v in stage_hits.values())
            report["family_results"][family] = {
                "query_id": q.get("query_id"),
                "missing_expected_papers": missing_expected_papers,
                "missing_expected_source_chunk_ids": missing_expected_sources,
                "stage_hits": stage_hits,
                "status": "PASS" if ok else "BLOCKED",
            }

        all_pass = all(v.get("status") == "PASS" for v in report["family_results"].values())
        report["status"] = "PASS" if (all_pass and not missing_families) else "BLOCKED"

    except Exception as exc:
        report["status"] = "BLOCKED"
        report["error"] = str(exc)

    write_json(out_dir / "real_golden_small_smoke.json", report)
    lines = [
        f"- status: {report['status']}",
        f"- selected_count: {report['selected_count']}",
        f"- missing_families: {', '.join(report['missing_families']) if report['missing_families'] else 'none'}",
        "",
        "| family | query_id | status |",
        "|---|---|---|",
    ]
    for fam in REQUIRED_FAMILIES:
        r = report["family_results"].get(fam)
        if not r:
            lines.append(f"| {fam} | - | BLOCKED |")
            continue
        lines.append(f"| {fam} | {r.get('query_id')} | {r.get('status')} |")

    if report.get("error"):
        lines.extend(["", "## Error", f"- {report['error']}"])
    write_markdown(out_dir / "real_golden_small_smoke.md", "v2.5 Real Golden Small Smoke", lines)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
