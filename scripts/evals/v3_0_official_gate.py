#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "artifacts" / "benchmarks" / "v3_0"

PHASE7_THRESHOLDS = {
    "citation_coverage": 0.75,
    "unsupported_claim_rate": 0.30,
    "answer_evidence_consistency": 0.55,
}


def _run(cmd: list[str]) -> int:
    print("$", " ".join(cmd))
    return int(subprocess.run(cmd, cwd=ROOT).returncode)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _phase7_pass() -> tuple[bool, dict[str, Any]]:
    retrieval_path = OUTPUT_DIR / "hierarchical_16x3_results.json"
    quality_path = OUTPUT_DIR / "phase5_6_evidence_quality_raw.json"

    if not retrieval_path.exists() or not quality_path.exists():
        return False, {"reason": "missing_phase7_outputs"}

    retrieval = _load_json(retrieval_path)
    quality = _load_json(quality_path)

    retrieval_ok = retrieval.get("overall_verdict") == "PASS"
    summary = quality.get("summary", {})

    quality_ok = (
        float(summary.get("citation_coverage", 0.0)) >= PHASE7_THRESHOLDS["citation_coverage"]
        and float(summary.get("unsupported_claim_rate", 1.0)) <= PHASE7_THRESHOLDS["unsupported_claim_rate"]
        and float(summary.get("answer_evidence_consistency", 0.0)) >= PHASE7_THRESHOLDS["answer_evidence_consistency"]
    )

    detail = {
        "retrieval_ok": retrieval_ok,
        "quality_ok": quality_ok,
        "quality_summary": summary,
    }
    return bool(retrieval_ok and quality_ok), detail


def _fallback_snapshot(phase7_quality_summary: dict[str, Any] | None = None) -> dict[str, Any]:
    summary = phase7_quality_summary or {}
    fallback_used_count = int(summary.get("fallback_used_count", 0))
    unsupported_count = int(summary.get("unsupported_field_type_count", 0))
    return {
        "unsupported_field_type_count": unsupported_count,
        "fallback_used_count": fallback_used_count,
        "fallback_reasons": [],
        "fallback_stages": [],
        "id_only_success_count": 0,
        "hydration_success_rate": 1.0,
        "strict_gate_ready": unsupported_count == 0 and fallback_used_count == 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="v3.0 official 64/80x3 gate")
    parser.add_argument("--python", default="/Users/cc/.virtualenvs/scholar-ai-api/bin/python")
    parser.add_argument("--official-max-queries", type=int, default=80)
    parser.add_argument("--milvus-host", default="localhost")
    parser.add_argument("--milvus-port", type=int, default=19530)
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    rc = _run(
        [
            args.python,
            "scripts/evals/v3_0_hierarchical_retrieval_regression.py",
            "--max-queries",
            "16",
            "--milvus-host",
            args.milvus_host,
            "--milvus-port",
            str(args.milvus_port),
        ]
    )
    if rc != 0:
        print("[v3.0 official gate] Phase 7 retrieval regression failed")
        return rc

    rc = _run(
        [
            args.python,
            "scripts/evals/v3_0_evidence_quality_eval.py",
            "--stage",
            "raw",
            "--max-queries",
            "16",
            "--milvus-host",
            args.milvus_host,
            "--milvus-port",
            str(args.milvus_port),
        ]
    )
    if rc != 0:
        print("[v3.0 official gate] Phase 7 quality eval failed")
        return rc

    phase7_ok, phase7_detail = _phase7_pass()
    if not phase7_ok:
        print("[v3.0 official gate] Phase 7 thresholds not met, skip official 64/80x3")
        payload = {
            "overall_verdict": "BLOCKED",
            "phase7": phase7_detail,
            "fallback_snapshot": _fallback_snapshot(phase7_detail.get("quality_summary", {})),
            "official_max_queries": args.official_max_queries,
        }
        out_json = OUTPUT_DIR / "official_gate_results.json"
        out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return 1

    official_results: dict[str, Any] = {"stages": []}
    for stage in ("raw", "rule", "llm"):
        rc = _run(
            [
                args.python,
                "scripts/evals/v3_0_paper_section_recall_eval.py",
                "--stage",
                stage,
                "--max-queries",
                str(args.official_max_queries),
                "--milvus-host",
                args.milvus_host,
                "--milvus-port",
                str(args.milvus_port),
            ]
        )
        if rc != 0:
            print(f"[v3.0 official gate] stage={stage} eval failed")
            return rc

        path = OUTPUT_DIR / f"phase1_paper_section_recall_{stage}.json"
        data = _load_json(path)
        official_results["stages"].append(
            {
                "stage": stage,
                "verdict": data.get("verdict"),
                "summary": data.get("summary", {}).get("overall", {}),
            }
        )

    official_results["overall_verdict"] = (
        "PASS" if all(s["verdict"] == "PASS" for s in official_results["stages"]) else "PARTIAL"
    )
    official_results["official_max_queries"] = args.official_max_queries
    official_results["phase7"] = phase7_detail
    official_results["fallback_snapshot"] = _fallback_snapshot(phase7_detail.get("quality_summary", {}))

    out_json = OUTPUT_DIR / "official_gate_results.json"
    out_json.write_text(json.dumps(official_results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[v3.0 official gate] saved: {out_json}")
    return 0 if official_results["overall_verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
