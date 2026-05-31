#!/usr/bin/env python3
"""v5.0 consolidated release gate runner.

Reads 5 input faces (audit / benchmark / walkthrough / governance / perf),
outputs a three-state verdict: release-pass | experiment-only | blocked.

Source of truth: docs/plans/v5_0/active/phase_0/v5_0_gate_input_matrix.md
Upgraded from: scripts/evals/run_v4_phase7_gate.py
"""
from __future__ import annotations

import argparse
import glob
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

# Paths — declared explicitly per matrix §6.2
_AUDIT_GLOB = str(ROOT / "docs" / "plans" / "v5_0" / "reports" / "*_multidimensional_audit.md")
_BENCH_DIR = ROOT / "artifacts" / "validation-results" / "v5_0"
_WALKTHROUGH = ROOT / "artifacts" / "walkthrough" / "v5_0" / "latest_summary.json"
_PLAYWRIGHT = ROOT / "apps" / "web" / "playwright-report"
_PERF_DIR = ROOT / "artifacts" / "perf" / "v5_0"
_PLAN_STATUS = ROOT / "docs" / "plans" / "PLAN_STATUS.md"

_GOVERNANCE_CHECKS: dict[str, tuple[str, ...]] = {
    "doc_governance": ("bash", str(ROOT / "scripts" / "check-doc-governance.sh")),
    "plan_governance": ("bash", str(ROOT / "scripts" / "check-plan-governance.sh")),
    "phase_tracking": ("bash", str(ROOT / "scripts" / "check-phase-tracking.sh")),
    "governance": ("bash", str(ROOT / "scripts" / "check-governance.sh")),
    "runtime_hygiene": ("bash", str(ROOT / "scripts" / "check-runtime-hygiene.sh"), "tracked"),
}
_REQUIRED_DIMS = {"frontend", "backend", "rag", "governance", "perf"}
_ROUTES = {"route_landing": "/", "route_kb": "/kb", "route_read": "/read", "route_chat": "/chat"}

RELEASE_PASS = "release-pass"
EXPERIMENT_ONLY = "experiment-only"
BLOCKED = "blocked"
_GATE_VERSION = "5.0-0"


# -- helpers ----------------------------------------------------------------

def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")

def _json(p: Path) -> dict[str, Any]:
    return json.loads(_read(p))

def _glob_sorted(pat: str) -> list[Path]:
    return sorted(Path(x) for x in glob.glob(pat))

def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")

def _blocked(reason: str, d: dict) -> tuple[bool, dict]:
    d["pass"] = False; d["block_reason"] = reason
    return False, d

def _ok(d: dict) -> tuple[bool, dict]:
    d["pass"] = True
    return True, d


# -- Face A: Audit ----------------------------------------------------------
# matrix §2 Face A: p1_count_open == 0 => PASS, >0 => BLOCK

def _evaluate_face_a(audit_glob: str | None = None) -> tuple[bool, dict]:
    pat = audit_glob or _AUDIT_GLOB
    files = _glob_sorted(pat)
    stub: dict[str, Any] = {"p1_count_open": None, "p2_count_open": None,
        "last_audit_date": None, "audit_dimensions_covered": [], "audit_report_path": None}
    if not files:
        return _blocked("input_missing", stub)

    latest = files[-1]
    text = _read(latest)
    m1 = re.search(r"p1_count_open[:\s]+`?(\d+)`?", text)
    m2 = re.search(r"p2_count_open[:\s]+`?(\d+)`?", text)
    md = re.search(r"last_audit_date[:\s]+`?(\d{4}-\d{2}-\d{2})`?", text)
    mx = re.search(r"audit_dimensions_covered[:\s]+`?\[([^\]]*)\]`?", text)

    p1 = int(m1.group(1)) if m1 else -1
    p2 = int(m2.group(1)) if m2 else 0
    dims = [d.strip().strip('"\'') for d in mx.group(1).split(",") if d.strip()] if mx else []

    d: dict[str, Any] = {"p1_count_open": p1, "p2_count_open": p2,
        "last_audit_date": md.group(1) if md else None,
        "audit_dimensions_covered": dims, "audit_report_path": str(latest.relative_to(ROOT))}

    if p1 < 0:
        return _blocked("p1_count_unparseable", d)
    if p1 > 0:
        return _blocked(f"p1_open={p1}", d)
    if set(dims) != _REQUIRED_DIMS:
        d["downgrade_reason"] = f"audit_dimensions_incomplete: {sorted(set(dims))}"
        d["experiment_only"] = True
    return _ok(d)


# -- Face B: Benchmark ------------------------------------------------------
# matrix §2 Face B: regression|academic_fail|workflow_fail => BLOCK; rag skipped => experiment-only

def _evaluate_face_b(bench_dir: str | None = None) -> tuple[bool, dict]:
    base = Path(bench_dir) if bench_dir else _BENCH_DIR
    stub: dict[str, Any] = {"academic_run_id": None, "academic_verdict": None,
        "workflow_run_id": None, "workflow_verdict": None, "rag_comparative_verdict": None,
        "regression_flag": None, "last_benchmark_date": None}
    if not base.exists():
        return _blocked("input_missing", stub)

    def _latest(glob_pat: str) -> list[Path]:
        return sorted(base.glob(glob_pat))

    acad = _latest("*/academic_bench_*.json")
    wf = _latest("*/workflow_bench_*.json")
    rag = _latest("*/rag_comparative_verdict_*.json")

    def _v(files: list[Path]) -> tuple[str | None, str | None]:
        if not files:
            return None, None
        data = _json(files[-1])
        return data.get("run_id"), data.get("verdict", data.get("overall_verdict"))

    a_id, a_ver = _v(acad)
    w_id, w_ver = _v(wf)
    r_ver = _json(rag[-1]).get("verdict") if rag else None
    regression = any(_json(f).get("regression_flag") is True for f in acad + wf)

    d: dict[str, Any] = {"academic_run_id": a_id, "academic_verdict": a_ver,
        "workflow_run_id": w_id, "workflow_verdict": w_ver,
        "rag_comparative_verdict": r_ver, "regression_flag": regression,
        "last_benchmark_date": None}

    if a_ver is None:
        return _blocked("academic_artifact_missing", d)
    if w_ver is None:
        return _blocked("workflow_artifact_missing", d)
    if regression:
        return _blocked("regression_detected", d)
    if str(a_ver).lower() == "fail":
        return _blocked("academic_fail", d)
    if str(w_ver).lower() == "fail":
        return _blocked("workflow_fail", d)
    if r_ver is None or str(r_ver).lower() == "skipped":
        d["downgrade_reason"] = "rag_comparative_skipped"
        d["experiment_only"] = True
    return _ok(d)


# -- Face C: Walkthrough (Playwright E2E 7 journeys) -----------------------
# matrix §2 Face C: all 7 pass => BLOCK if fail>0 or passed<7; skipped>0 => experiment-only

_EXPECTED_J = 7

def _evaluate_face_c() -> tuple[bool, dict]:
    stub: dict[str, Any] = {"journey_passed_count": None, "journey_failed_count": None,
        "journey_skipped_count": None, "journey_details": [],
        "last_run_at": None, "playwright_report_path": None}
    if not _WALKTHROUGH.exists():
        return _blocked("input_missing", stub)

    data = _json(_WALKTHROUGH)
    p = data.get("journey_passed_count", 0)
    f = data.get("journey_failed_count", 0)
    s = data.get("journey_skipped_count", 0)
    d: dict[str, Any] = {"journey_passed_count": p, "journey_failed_count": f,
        "journey_skipped_count": s, "journey_details": data.get("journey_details", []),
        "last_run_at": data.get("last_run_at"),
        "playwright_report_path": data.get("playwright_report_path", str(_PLAYWRIGHT.relative_to(ROOT)))}

    if f > 0 or p < _EXPECTED_J:
        return _blocked(f"journeys_passed={p}/7, failed={f}", d)
    if s > 0:
        d["downgrade_reason"] = f"journeys_skipped={s}"
        d["experiment_only"] = True
    return _ok(d)


# -- Face D: Governance (5 check scripts + phase closeout) ------------------
# matrix §2 Face D: all 6 booleans true => PASS

def _run_script(cmd: tuple[str, ...]) -> bool:
    try:
        return subprocess.run(cmd, capture_output=True, timeout=60, cwd=str(ROOT)).returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False

def _phases_closed() -> bool:
    if not _PLAN_STATUS.exists():
        return False
    text = _read(_PLAN_STATUS)
    return all(re.search(rf"5\.0-{n}\b.*\bdone\b", text, re.I) for n in range(10))

def _evaluate_face_d() -> tuple[bool, dict]:
    checks = {k: _run_script(v) for k, v in _GOVERNANCE_CHECKS.items()}
    checks["all_phases_closeout"] = _phases_closed()
    d: dict[str, Any] = {**checks, "governance_check_timestamp": _now()}
    if not all(checks.values()):
        return _blocked(f"checks_failed={[k for k,v in checks.items() if not v]}", d)
    return _ok(d)


# -- Face E: Perf (Lighthouse + Bundle) ------------------------------------
# matrix §2 Face E: lighthouse_min>=90, bundle<=500KB gz, lcp<2500, inp<200, cls<0.05

def _evaluate_face_e(perf_dir: str | None = None) -> tuple[bool, dict]:
    pdir = Path(perf_dir) if perf_dir else _PERF_DIR
    stub: dict[str, Any] = {"lighthouse_scores": {}, "lighthouse_min_score": None,
        "bundle_first_screen_kb_gz": None, "bundle_total_main_routes_kb_gz": None,
        "cwv_lcp_ms": None, "cwv_inp_ms": None, "cwv_cls": None,
        "cwv_fcp_ms": None, "cwv_tbt_ms": None, "perf_snapshot_date": None}
    if not pdir.exists():
        return _blocked("input_missing", stub)

    scores: dict[str, int] = {}
    cwv = {"lcp": 0.0, "inp": 0.0, "cls": 0.0, "fcp": 0.0, "tbt": 0.0}
    snap: str | None = None

    for rid in _ROUTES:
        files = _glob_sorted(str(pdir / f"lighthouse-{rid}*.json"))
        if not files:
            return _blocked(f"lighthouse_missing_{rid}", {**stub, "lighthouse_scores": scores})
        data = _json(files[-1])
        cat = data.get("categories", {}).get("performance", {})
        raw = cat.get("score", 0)
        scores[rid] = int(raw * 100) if isinstance(raw, float) and raw <= 1 else int(raw)
        au = data.get("audits", {})
        cwv["lcp"] = max(cwv["lcp"], au.get("largest-contentful-paint", {}).get("numericValue", 0))
        cwv["inp"] = max(cwv["inp"], au.get("interactive", {}).get("numericValue", 0))
        cwv["cls"] = max(cwv["cls"], au.get("cumulative-layout-shift", {}).get("numericValue", 0))
        cwv["fcp"] = max(cwv["fcp"], au.get("first-contentful-paint", {}).get("numericValue", 0))
        cwv["tbt"] = max(cwv["tbt"], au.get("total-blocking-time", {}).get("numericValue", 0))
        ft = data.get("fetchTime", data.get("generatedTime"))
        if ft and (snap is None or ft > snap):
            snap = ft

    mn = min(scores.values())
    # Bundle from dist/stats.html
    bf = bg = None
    sp = ROOT / "apps" / "web" / "dist" / "stats.html"
    if sp.exists():
        nums = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s*KB.*?gzip", _read(sp), re.I)]
        if nums:
            bf, bg = round(nums[0], 1), round(sum(nums), 1)

    d: dict[str, Any] = {"lighthouse_scores": scores, "lighthouse_min_score": mn,
        "bundle_first_screen_kb_gz": bf, "bundle_total_main_routes_kb_gz": bg,
        "cwv_lcp_ms": round(cwv["lcp"], 1), "cwv_inp_ms": round(cwv["inp"], 1),
        "cwv_cls": round(cwv["cls"], 4), "cwv_fcp_ms": round(cwv["fcp"], 1),
        "cwv_tbt_ms": round(cwv["tbt"], 1), "perf_snapshot_date": snap}

    if mn < 90:
        return _blocked(f"lighthouse_min={mn}<90", d)
    if bg is not None and bg > 500:
        return _blocked(f"bundle_total={bg}>500KB", d)
    if cwv["lcp"] >= 2500:
        return _blocked(f"lcp={cwv['lcp']:.0f}ms>=2500", d)
    if cwv["inp"] >= 200:
        return _blocked(f"inp={cwv['inp']:.0f}ms>=200", d)
    if cwv["cls"] >= 0.05:
        return _blocked(f"cls={cwv['cls']:.4f}>=0.05", d)
    return _ok(d)


# -- Verdict aggregation (matrix §3) ----------------------------------------

def _verdict(faces: dict[str, tuple[bool, dict]]) -> tuple[str, list[str], list[str]]:
    blocks, downgrades = [], []
    for k, (passed, d) in faces.items():
        if not passed:
            blocks.append(f"{k}: {d.get('block_reason', 'unknown')}")
        if d.get("experiment_only"):
            downgrades.append(f"{k}: {d.get('downgrade_reason', 'unknown')}")
    if blocks:
        return BLOCKED, blocks, downgrades
    if downgrades:
        return EXPERIMENT_ONLY, blocks, downgrades
    return RELEASE_PASS, blocks, downgrades


# -- Report generation -------------------------------------------------------

_LABELS = {"face_a": "Face A -- Audit", "face_b": "Face B -- Benchmark",
    "face_c": "Face C -- Walkthrough", "face_d": "Face D -- Governance", "face_e": "Face E -- Perf"}
_BADGE = {RELEASE_PASS: "RELEASE-PASS", EXPERIMENT_ONLY: "EXPERIMENT-ONLY", BLOCKED: "BLOCKED"}
_RECOMMEND = {BLOCKED: "Hold release. Resolve all block reasons before re-running.",
    EXPERIMENT_ONLY: "Ship as experiment-only. Resolve downgrades for release-pass.",
    RELEASE_PASS: "Allow release-pass. All gates satisfied."}

def _report_md(verdict: str, faces: dict[str, tuple[bool, dict]],
               blocks: list[str], downgrades: list[str]) -> str:
    L: list[str] = []
    L.append(f"# v5.0 Release Gate Report -- {_today()}\n")
    L.append(f"## Verdict: {_BADGE[verdict]}")
    L.append(f"> gate_version: `{_GATE_VERSION}`  |  generated_at: `{_now()}`\n")
    L.append("## Face Results\n")
    L.append("| Face | Result | Key Detail |")
    L.append("|------|--------|------------|")
    for k, lbl in _LABELS.items():
        p, d = faces[k]
        tag = "PASS" if p else "BLOCK"
        r = d.get("block_reason", d.get("downgrade_reason", "--"))
        L.append(f"| {lbl} | **{tag}** | {r} |")
    L.append("")
    skip = {"pass", "block_reason", "experiment_only", "downgrade_reason"}
    for k, lbl in _LABELS.items():
        p, d = faces[k]
        L.append(f"## {lbl}\n\nStatus: **{'PASS' if p else 'BLOCK'}**\n")
        for fk, fv in d.items():
            if fk not in skip:
                L.append(f"- `{fk}`: {json.dumps(fv, ensure_ascii=False)}")
        L.append("")
    if blocks:
        L.append("## Block Reasons\n")
        L.extend(f"- {r}" for r in blocks)
        L.append("")
    if downgrades:
        L.append("## Downgrade Reasons\n")
        L.extend(f"- {r}" for r in downgrades)
        L.append("")
    L.append("## Recommended Next Actions\n")
    L.append(f"- {_RECOMMEND[verdict]}")
    if verdict == BLOCKED:
        L.append("- Priority: resolve block reasons in order above.")
        L.append("- Re-run: `python scripts/evals/run_v5_release_gate.py`")
    return "\n".join(L)


# -- CLI --------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="v5.0 consolidated release gate (5-face)")
    ap.add_argument("--audit-report", default=None, help="Glob for audit reports")
    ap.add_argument("--benchmark-dir", default=None, help="Benchmark artifacts dir")
    ap.add_argument("--playwright-report", default=None, help="Playwright report dir")
    ap.add_argument("--governance-baseline", default="v5_0", help="Governance baseline tag")
    ap.add_argument("--perf-dir", default=None, help="Lighthouse/perf artifacts dir")
    ap.add_argument("--output-json", default=None, help="JSON output path")
    ap.add_argument("--output-md", default=None, help="Markdown report path")
    args = ap.parse_args()

    faces: dict[str, tuple[bool, dict]] = {
        "face_a": _evaluate_face_a(args.audit_report),
        "face_b": _evaluate_face_b(args.benchmark_dir),
        "face_c": _evaluate_face_c(),
        "face_d": _evaluate_face_d(),
        "face_e": _evaluate_face_e(args.perf_dir),
    }

    verdict, blocks, downgrades = _verdict(faces)

    faces_json = {}
    for k, (p, d) in faces.items():
        c = {fk: fv for fk, fv in d.items() if fk != "experiment_only"}
        c["pass"] = p
        faces_json[k] = c

    result: dict[str, Any] = {"run_id": _now(), "gate_version": _GATE_VERSION,
        "verdict": verdict, "faces": faces_json,
        "block_reasons": blocks, "downgrade_reasons": downgrades, "generated_at": _now()}

    jp = Path(args.output_json) if args.output_json else ROOT / "artifacts" / "validation-results" / "v5_0" / "phase0_gate_results.json"
    jp.parent.mkdir(parents=True, exist_ok=True)
    jp.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    mp = Path(args.output_md) if args.output_md else ROOT / "docs" / "plans" / "v5_0" / "reports" / f"{_today()}_v5_0_phase_0_gate_report.md"
    mp.parent.mkdir(parents=True, exist_ok=True)
    mp.write_text(_report_md(verdict, faces, blocks, downgrades), encoding="utf-8")

    print(f"[v5.0-gate] verdict={verdict}")
    print(f"[v5.0-gate] json={jp}")
    print(f"[v5.0-gate] report={mp}")
    if blocks:
        print(f"[v5.0-gate] blocked_by={', '.join(blocks)}")
    if downgrades:
        print(f"[v5.0-gate] downgrades={', '.join(downgrades)}")

    return 0 if verdict == RELEASE_PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
