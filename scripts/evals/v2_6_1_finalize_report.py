#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List

from scripts.evals.v2_6_1_common import read_json, write_markdown


ROOT = Path(__file__).resolve().parents[2]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Step6.1 final diagnosis report")
    p.add_argument("--report-dir", default=str(ROOT / "artifacts" / "benchmarks" / "v2_6_1"))
    return p.parse_args()


def _load(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return read_json(path)


def classify(a: Dict[str, Any], b: Dict[str, Any], d: Dict[str, Any], e: Dict[str, Any], f: Dict[str, Any], g: Dict[str, Any]) -> str:
    a_categories = set(a.get("blocked_categories") or [])
    if "FIELD_MAPPING_ERROR" in a_categories or "EVAL_ALIGNMENT_ERROR" in a_categories:
        return "EVAL_ALIGNMENT_ERROR"

    b_pass = b.get("status") == "PASS"
    if not b_pass:
        return "INGEST_ALIGNMENT_ERROR"

    if f.get("full_expr_suspected_filter_bug_count", 0) > 0:
        return "RETRIEVAL_RUNTIME_ERROR"

    if e.get("embedding_space_mismatch") is True:
        return "EMBEDDING_SPACE_MISMATCH"

    if d.get("summary", {}).get("oracle_missing", 0) > 0:
        return "EVAL_ALIGNMENT_ERROR"

    return "QUALITY_ERROR"


def recommendation(category: str) -> List[str]:
    if category == "EVAL_ALIGNMENT_ERROR":
        return [
            "修复 golden generation 与 source_chunk_id 映射，确认 expected_source_chunk_ids 可在 collection 定位。",
            "保持 embedding/reranker/LLM 不变，不做模型调参。",
        ]
    if category == "INGEST_ALIGNMENT_ERROR":
        return [
            "修复 v2_4 ingestion 的 source_chunk_id 写入与 stage 对齐。",
            "仅在 ingestion 修复后评估是否需要重建 v2_4 collection。",
        ]
    if category == "RETRIEVAL_RUNTIME_ERROR":
        return [
            "修复 runner/registry/output_fields/hydration 的 source_chunk_id 取值链路。",
            "优先修逻辑，不重建 collection。",
        ]
    if category == "EMBEDDING_SPACE_MISMATCH":
        return [
            "统一 query embedding 与 corpus embedding provider/model 元数据。",
            "必要时在模型统一后重建 collection。",
        ]
    return [
        "进入 retrieval quality tuning：query rewrite、hybrid sparse、增大 rerank 前候选。",
        "在质量优化前保持现有 runtime 合约不变。",
    ]


def main() -> int:
    args = parse_args()
    report_dir = Path(args.report_dir)

    a = _load(report_dir / "source_chunk_id_existence_report.json")
    b = _load(report_dir / "collection_artifact_alignment_report.json")
    d = _load(report_dir / "oracle_recall_report.json")
    e = _load(report_dir / "query_embedding_consistency_report.json")
    f = _load(report_dir / "filter_expr_diagnostic_report.json")
    g = _load(report_dir / "neighbor_overlap_report.json")

    category = classify(a, b, d, e, f, g)
    rerun_allowed = "ALLOWED" if category in {"RETRIEVAL_RUNTIME_ERROR", "QUALITY_ERROR"} else "NOT_ALLOWED"
    diagnosis_status = "PASS" if category == "QUALITY_ERROR" else "BLOCKED"

    recs = recommendation(category)

    lines = [
        "## Step6 Regression 原始结果",
        "",
        "- total: 48",
        "- recall_at_10: 0.0",
        "- citation_coverage: 0.743",
        "- unsupported_claim_rate: 0.451",
        "- answer_evidence_consistency: 0.319",
        "- final_gate: BLOCKED",
        "",
        "## Step6.1 诊断摘要",
        "",
        f"- expected source id existence: {a.get('status', 'UNKNOWN')}",
        f"- artifact vs collection alignment: {b.get('status', 'UNKNOWN')}",
        f"- oracle recall: {d.get('status', 'UNKNOWN')}",
        f"- query embedding consistency: {e.get('status', 'UNKNOWN')}",
        f"- filter expr diagnostic: {f.get('status', 'UNKNOWN')}",
        f"- neighbor overlap exact_chunk_hit_rate: {g.get('summary', {}).get('exact_chunk_hit_rate', 'N/A')}",
        "",
        "## Final Diagnosis",
        "",
        f"- Step6.1 diagnosis: {diagnosis_status}",
        f"- Blocked category: {category}",
        f"- Step6 rerun allowed: {rerun_allowed}",
        "",
        "## Recommended Fix",
    ]
    for item in recs:
        lines.append(f"- {item}")

    artifact_report = report_dir / "step6_1_recall_debug_report.md"
    docs_report = ROOT / "docs" / "reports" / "official_rag_evaluation" / "step6_1_recall_debug_report.md"
    write_markdown(artifact_report, "Step6.1 Retrieval Recall Debug Report", lines)
    write_markdown(docs_report, "Step6.1 Retrieval Recall Debug Report", lines)
    print(artifact_report)
    print(docs_report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
