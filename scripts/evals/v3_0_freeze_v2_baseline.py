#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.evals.v2_4_common import read_json, write_json, write_markdown

ARTIFACT_DIR = ROOT / "artifacts" / "benchmarks" / "v3_0"
DOC_DIR = ROOT / "docs" / "reports" / "v3_0"

STEP6_2_MD = ROOT / "artifacts" / "benchmarks" / "v2_6_2" / "step6_2_retrieval_quality_report.md"
BASELINE_MD = ROOT / "artifacts" / "benchmarks" / "v2_6_2" / "baseline_retrieval_quality.md"
TUNED_JSON = ROOT / "artifacts" / "benchmarks" / "v2_6_2" / "v2_6_2_tuned_16x3_results.json"

OUTPUT_JSON = ARTIFACT_DIR / "v2_failure_baseline.json"
OUTPUT_MD = DOC_DIR / "v2_failure_baseline.md"


EXPECTED_KEYS = {
    "recall_at_10",
    "recall_at_50",
    "recall_at_100",
    "same_paper_hit_rate",
    "citation_coverage",
    "unsupported_claim_rate",
    "answer_evidence_consistency",
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract_metric(text: str, key: str) -> float | None:
    match = re.search(rf"{re.escape(key)}\s*:\s*([0-9]+(?:\.[0-9]+)?)", text)
    if not match:
        return None
    return float(match.group(1))


def build_baseline_payload() -> dict[str, Any]:
    if not STEP6_2_MD.exists() or not BASELINE_MD.exists() or not TUNED_JSON.exists():
        missing = [str(path) for path in [STEP6_2_MD, BASELINE_MD, TUNED_JSON] if not path.exists()]
        raise FileNotFoundError(f"missing required v2_6_2 inputs: {missing}")

    step62_text = STEP6_2_MD.read_text(encoding="utf-8")
    baseline_text = BASELINE_MD.read_text(encoding="utf-8")
    tuned_json = read_json(TUNED_JSON)

    metrics = {
        "recall_at_10": extract_metric(step62_text, "recall_at_10"),
        "same_paper_hit_rate": extract_metric(step62_text, "same_paper_hit_rate"),
        "citation_coverage": extract_metric(step62_text, "citation_coverage"),
        "unsupported_claim_rate": extract_metric(step62_text, "unsupported_claim_rate"),
        "answer_evidence_consistency": extract_metric(step62_text, "answer_evidence_consistency"),
        "recall_at_50": extract_metric(baseline_text, "overall_recall_at_50"),
        "recall_at_100": extract_metric(baseline_text, "overall_recall_at_100"),
    }

    missing_metrics = sorted(key for key, value in metrics.items() if value is None)
    if missing_metrics:
        raise ValueError(f"missing baseline metrics: {missing_metrics}")

    return {
        "version": "v3.0-phase0",
        "status": "FROZEN",
        "source": "v2_6_2",
        "constraints": {
            "modify_step5_real_golden": False,
            "reparse_pdf": False,
            "rechunk": False,
            "rebuild_v2_4_collection": False,
            "replace_primary_embedding_model": False,
            "allow_bge_specter2_local_qwen_in_main_chain": False,
            "allow_official_64_80x3": False,
        },
        "metrics": metrics,
        "gate": {
            "retrieval_tuning": "BLOCKED",
            "step6_regression_rerun": "NOT_ALLOWED",
            "official_64_80x3": "NOT_ALLOWED",
        },
        "required_failure_buckets": [
            "paper_miss",
            "section_miss",
            "candidate_pool_miss",
            "reranker_miss",
            "answer_verification_miss",
        ],
        "traceability": {
            "inputs": {
                "step6_2_report": str(STEP6_2_MD.relative_to(ROOT)),
                "baseline_retrieval_report": str(BASELINE_MD.relative_to(ROOT)),
                "tuned_16x3_results": str(TUNED_JSON.relative_to(ROOT)),
            },
            "input_sha256": {
                "step6_2_report": sha256_file(STEP6_2_MD),
                "baseline_retrieval_report": sha256_file(BASELINE_MD),
                "tuned_16x3_results": sha256_file(TUNED_JSON),
            },
            "records": int(len(tuned_json.get("records", []))),
        },
    }


def build_markdown_lines(payload: dict[str, Any]) -> list[str]:
    metrics = payload["metrics"]
    lines = [
        "## Frozen Baseline",
        "",
        "- source: v2_6_2",
        "- status: FROZEN",
        "- retrieval_tuning: BLOCKED",
        "- step6_regression_rerun: NOT_ALLOWED",
        "- official_64_80x3: NOT_ALLOWED",
        "",
        "## Metrics",
        "",
        f"- recall@10: {metrics['recall_at_10']}",
        f"- recall@50: {metrics['recall_at_50']}",
        f"- recall@100: {metrics['recall_at_100']}",
        f"- same_paper_hit_rate: {metrics['same_paper_hit_rate']}",
        f"- citation_coverage: {metrics['citation_coverage']}",
        f"- unsupported_claim_rate: {metrics['unsupported_claim_rate']}",
        f"- answer_evidence_consistency: {metrics['answer_evidence_consistency']}",
        "",
        "## Hard Constraints",
        "",
        "- do not modify Step5 real golden",
        "- do not re-parse PDF / re-chunk",
        "- do not rebuild v2_4 evidence chunk collection",
        "- do not replace primary embedding model",
        "- do not re-introduce BGE/SPECTER2/local qwen into main chain",
        "- do not run official 64/80x3 before v3 16x3 pass",
    ]
    return lines


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Freeze v2_6_2 failure baseline for v3.0")
    parser.add_argument("--strict", action="store_true", default=False)
    return parser.parse_args()


def main() -> int:
    _ = parse_args()
    payload = build_baseline_payload()

    metrics = payload.get("metrics", {})
    missing = EXPECTED_KEYS - set(metrics.keys())
    if missing:
        raise ValueError(f"missing expected keys in payload metrics: {sorted(missing)}")

    write_json(OUTPUT_JSON, payload)
    write_markdown(OUTPUT_MD, "ScholarAI v3.0 - v2 Failure Baseline", build_markdown_lines(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
