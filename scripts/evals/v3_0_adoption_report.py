#!/usr/bin/env python3
"""Generate v3.0 academic benchmark adoption report from artifacts."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V3_ROOT = ROOT / "apps" / "api" / "artifacts" / "benchmarks" / "v3_0_academic"
OUT_MD = ROOT / "docs" / "reports" / "v3_0_academic_adoption_report.md"


def _load(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    public_corpus = _load(V3_ROOT / "corpus_public.json")
    blind_corpus = _load(V3_ROOT / "corpus_blind.json")
    manifest = _load(V3_ROOT / "manifest.json")

    runs = list(reversed(manifest.get("runs") or []))
    baseline = next((r for r in runs if r.get("baseline_for")), None)
    candidate = runs[0] if runs else None

    lines = [
        "# v3.0 Academic Benchmark Adoption Report",
        "",
        f"- dataset_version: {public_corpus.get('dataset_version', 'unknown')}",
        f"- public split: {public_corpus.get('split', 'unknown')}",
        f"- blind split: {blind_corpus.get('split', 'unknown')}",
        f"- paper_count: {public_corpus.get('paper_count', 0)}",
        f"- query_count: {public_corpus.get('query_count', 0)}",
        f"- manifest_run_count: {len(runs)}",
        "",
        "## Run Snapshot",
        "",
        f"- baseline_run: {baseline.get('run_id') if baseline else 'N/A'}",
        f"- candidate_run: {candidate.get('run_id') if candidate else 'N/A'}",
        "",
        "## Family Coverage",
        "",
    ]

    family_quota = public_corpus.get("family_quota") or {}
    for family, count in sorted(family_quota.items()):
        lines.append(f"- {family}: {count}")

    lines.extend([
        "",
        "## Notes",
        "",
        "- formula 在 P0 按 kickoff freeze 保持 report-only。",
        "- blind split 为 score-only 访问模式。",
    ])

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"report={OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
