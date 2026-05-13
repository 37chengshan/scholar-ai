#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PLAN_STATUS_PATH = ROOT / "docs" / "plans" / "PLAN_STATUS.md"
PHASE2_REPORT_PATH = (
    ROOT / "docs" / "plans" / "v4_0" / "reports" / "2026-05-08_v4_0_phase_2_controlled_beta_gate_report.md"
)
PHASE3_REPORT_PATH = ROOT / "docs" / "plans" / "v4_0" / "reports" / "2026-05-08_v4_0_phase_3_closeout_report.md"
PHASE_J_VERDICT_PATH = (
    ROOT
    / "artifacts"
    / "validation-results"
    / "phase_j"
    / "2026-04-30-closeout"
    / "comparative_verdict.json"
)
OFFICIAL_GATE_PATH = ROOT / "artifacts" / "benchmarks" / "v3_0" / "official_gate_results.json"

RELEASE_PASS = "release-pass"
EXPERIMENT_ONLY = "experiment-only"
BLOCKED = "blocked"


def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(_load_text(path))


def _read_markdown_verdict(path: Path) -> str | None:
    if not path.exists():
        return None
    text = _load_text(path)
    match = re.search(r"^>\s*verdict:\s*`?([A-Za-z0-9._/-]+)`?\s*$", text, flags=re.MULTILINE)
    if match:
        return match.group(1).strip()
    return None


def _parse_v4_phase_panel() -> dict[int, dict[str, str]]:
    text = _load_text(PLAN_STATUS_PATH)
    lines = text.splitlines()
    capture = False
    phases: dict[int, dict[str, str]] = {}
    for line in lines:
        if line.startswith("## v4.0 方向面板"):
            capture = True
            continue
        if capture and line.startswith("## ") and not line.startswith("## v4.0 方向面板"):
            break
        if not capture or not line.startswith("|"):
            continue
        if line.startswith("| phase |") or line.startswith("|---"):
            continue
        parts = [part.strip() for part in line.split("|")[1:-1]]
        if len(parts) < 6:
            continue
        try:
            phase_num = int(parts[0])
        except ValueError:
            continue
        phases[phase_num] = {
            "phase": parts[0],
            "owner": parts[1],
            "closeout_status": parts[2],
            "last_verified_at": parts[3],
            "truth_doc": parts[4],
            "notes": parts[5],
        }
    return phases


def _make_check(
    *,
    check_id: str,
    description: str,
    passed: bool,
    evidence: str,
    detail: str,
    severity: str = "required",
) -> dict[str, str]:
    return {
        "id": check_id,
        "description": description,
        "result": "pass" if passed else "fail",
        "severity": severity,
        "evidence": evidence,
        "detail": detail,
    }


def build_gate_result() -> dict[str, Any]:
    phase_panel = _parse_v4_phase_panel()
    phase2 = phase_panel.get(2, {})
    phase3 = phase_panel.get(3, {})
    phase4 = phase_panel.get(4, {})
    phase5 = phase_panel.get(5, {})
    phase6 = phase_panel.get(6, {})

    phase2_report_verdict = _read_markdown_verdict(PHASE2_REPORT_PATH)
    phase3_report_verdict = _read_markdown_verdict(PHASE3_REPORT_PATH)
    phase_j_verdict = _load_json(PHASE_J_VERDICT_PATH) if PHASE_J_VERDICT_PATH.exists() else {}
    official_gate = _load_json(OFFICIAL_GATE_PATH) if OFFICIAL_GATE_PATH.exists() else {}

    checks = [
        _make_check(
            check_id="phase2_controlled_beta",
            description="Phase 2 controlled beta gate is present and approved",
            passed=phase2_report_verdict == "controlled-beta-ready",
            evidence=str(PHASE2_REPORT_PATH.relative_to(ROOT)),
            detail=f"report verdict={phase2_report_verdict or 'missing'}",
        ),
        _make_check(
            check_id="phase3_artifact_closeout",
            description="Phase 3 artifact bundle is closed out to at least artifact-ready",
            passed=phase3_report_verdict in {"artifact-ready", "citation-backed-ready"},
            evidence=str(PHASE3_REPORT_PATH.relative_to(ROOT)),
            detail=f"report verdict={phase3_report_verdict or 'missing'}",
        ),
        _make_check(
            check_id="phase4_frontend_experience",
            description="Phase 4 frontend experience craft has completed closeout",
            passed=phase4.get("closeout_status", "").startswith("closeout-complete"),
            evidence="docs/plans/PLAN_STATUS.md",
            detail=f"status={phase4.get('closeout_status', 'missing')}",
        ),
        _make_check(
            check_id="phase5_frontend_interaction",
            description="Phase 5 frontend interaction quality has completed closeout",
            passed=phase5.get("closeout_status", "").startswith("closeout-complete"),
            evidence="docs/plans/PLAN_STATUS.md",
            detail=f"status={phase5.get('closeout_status', 'missing')}",
        ),
        _make_check(
            check_id="phase6_optimization_closeout",
            description="Phase 6 academic RAG optimization has completed final closeout",
            passed=phase6.get("closeout_status", "").startswith("closeout-complete"),
            evidence="docs/plans/PLAN_STATUS.md",
            detail=f"status={phase6.get('closeout_status', 'missing')}",
        ),
        _make_check(
            check_id="phase_j_comparative_gate",
            description="Comparative baseline-vs-candidate gate passes",
            passed=bool(phase_j_verdict.get("pass")) and phase_j_verdict.get("verdict") == "pass",
            evidence=str(PHASE_J_VERDICT_PATH.relative_to(ROOT)),
            detail=f"verdict={phase_j_verdict.get('verdict', 'missing')}",
        ),
        _make_check(
            check_id="official_academic_gate",
            description="Official academic gate artifact is PASS",
            passed=official_gate.get("overall_verdict") == "PASS",
            evidence=str(OFFICIAL_GATE_PATH.relative_to(ROOT)),
            detail=f"overall_verdict={official_gate.get('overall_verdict', 'missing')}",
        ),
    ]

    blocking_checks = [check for check in checks if check["result"] == "fail"]
    comparative_verdict = str(phase_j_verdict.get("verdict") or "").strip()

    if blocking_checks:
        verdict = BLOCKED
    elif comparative_verdict == EXPERIMENT_ONLY:
        verdict = EXPERIMENT_ONLY
    else:
        verdict = RELEASE_PASS

    recommendation = {
        BLOCKED: "hold-release",
        EXPERIMENT_ONLY: "keep-experiment-only",
        RELEASE_PASS: "allow-release-pass",
    }[verdict]

    return {
        "phase": "4.0-7",
        "generated_at": "2026-05-12",
        "verdict": verdict,
        "pass": verdict == RELEASE_PASS,
        "recommendation": recommendation,
        "blocking_items": [check["id"] for check in blocking_checks],
        "checks": checks,
        "upstream_phase_statuses": {
            "phase2": phase2,
            "phase3": phase3,
            "phase4": phase4,
            "phase5": phase5,
            "phase6": phase6,
        },
        "evidence_snapshot": {
            "phase2_report_verdict": phase2_report_verdict,
            "phase3_report_verdict": phase3_report_verdict,
            "phase_j_verdict": phase_j_verdict.get("verdict"),
            "official_gate_overall_verdict": official_gate.get("overall_verdict"),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the v4.0 Phase 7 testing and evaluation gate")
    parser.add_argument(
        "--output",
        default="artifacts/validation-results/phase_7/2026-05-12-gate/phase7_gate_results.json",
        help="Path to write the machine-readable gate result JSON",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Print JSON to stdout in addition to writing the file",
    )
    args = parser.parse_args()

    result = build_gate_result()
    output_path = ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[phase7] verdict={result['verdict']}")
    print(f"[phase7] saved={output_path}")
    if result["blocking_items"]:
        print(f"[phase7] blocking_items={', '.join(result['blocking_items'])}")

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))

    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
