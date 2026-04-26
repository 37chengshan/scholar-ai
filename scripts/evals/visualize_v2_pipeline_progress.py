#!/usr/bin/env python3
"""Terminal dashboard for v2/v2.1 parse-reuse pipeline progress."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Proc:
    pid: str
    cmd: str


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def detect_procs() -> list[Proc]:
    p = _run(["pgrep", "-fal", "run_academic_rag_v2.sh|run_academic_rag_v2_1.sh|prepare_raw_base.py|build_stage_variant.py|eval_retrieval.py|eval_answer.py"])
    if p.returncode != 0:
        return []
    rows: list[Proc] = []
    for line in p.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(" ", 1)
        if len(parts) != 2:
            continue
        rows.append(Proc(pid=parts[0], cmd=parts[1]))
    return rows


def _collection_name(profile: str, stage: str) -> str:
    if profile == "v2.1":
        return f"paper_contents_v2_qwen_v2_{stage}_v2_1"
    return f"paper_contents_v2_qwen_v2_{stage}_v2"


def get_collection_count(name: str) -> Optional[int]:
    try:
        from pymilvus import Collection, connections  # type: ignore
    except Exception:
        return None
    try:
        connections.connect(alias="v2viz", host="localhost", port=19530)
        c = Collection(name, using="v2viz")
        return int(c.num_entities)
    except Exception:
        return None


def read_json(path: Path) -> Optional[dict]:
    try:
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def clear_screen() -> None:
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def render(profile: str) -> str:
    out_dir = ROOT / "artifacts" / "benchmarks" / profile
    raw_base = out_dir / "raw_base" / "raw_chunks_manifest.json"
    summary_raw = out_dir / "variants" / "summary_raw.json"
    summary_rule = out_dir / "variants" / "summary_rule.json"
    summary_llm = out_dir / "variants" / "summary_llm.json"
    stage_timing = out_dir / "reports" / f"stage_timing_{profile}.json"

    raw_base_obj = read_json(raw_base)
    sum_raw = read_json(summary_raw)
    sum_rule = read_json(summary_rule)
    sum_llm = read_json(summary_llm)
    stage_timing_obj = read_json(stage_timing)
    total_chunks = int(raw_base_obj.get("total_chunks", 0)) if raw_base_obj else 0

    lines: list[str] = []
    lines.append(f"ScholarAI v2 Pipeline Dashboard ({profile})")
    lines.append(f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    lines.append("Stages:")
    lines.append(f"- prepare_raw_base: {'DONE' if raw_base_obj else 'PENDING'}")
    lines.append(f"- build:raw       : {'DONE' if sum_raw else 'PENDING'}")
    lines.append(f"- build:rule      : {'DONE' if sum_rule else 'PENDING'}")
    lines.append(f"- build:llm       : {'DONE' if sum_llm else 'PENDING'}")
    lines.append("")

    if raw_base_obj:
        lines.append("Raw Base:")
        lines.append(f"- papers={raw_base_obj.get('paper_count', 0)} chunks={raw_base_obj.get('total_chunks', 0)}")
        lines.append(f"- parse_pdf_seconds={raw_base_obj.get('parse_pdf_seconds', 0)}")
        lines.append(f"- chunk_raw_seconds={raw_base_obj.get('chunk_raw_seconds', 0)}")
        lines.append("")

    lines.append("Stored Chunks:")
    for stage in ("raw", "rule", "llm"):
        name = _collection_name(profile, stage)
        c = get_collection_count(name)
        if c is None:
            progress = "N/A"
        elif total_chunks > 0:
            progress = f"{c}/{total_chunks} ({(c / total_chunks) * 100:.1f}%)"
        else:
            progress = str(c)
        lines.append(f"- {stage:4s}: {progress} | {name}")
    lines.append("")

    if stage_timing_obj:
        lines.append("Stage Timing (seconds):")
        for k, v in sorted(stage_timing_obj.get("stage_timing_seconds", {}).items()):
            lines.append(f"- {k}: {v}")
        lines.append("")

    procs = detect_procs()
    lines.append("Processes:")
    if not procs:
        lines.append("- none")
    else:
        for p in procs:
            lines.append(f"- pid={p.pid} {p.cmd[:150]}")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Visualize v2/v2.1 pipeline progress")
    parser.add_argument("--profile", choices=["v2", "v2.1"], default="v2.1")
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--interval", type=int, default=5)
    args = parser.parse_args()

    if not args.watch:
        print(render(args.profile))
        return 0

    interval = max(1, int(args.interval))
    while True:
        clear_screen()
        print(render(args.profile))
        print("\nPress Ctrl+C to stop.")
        time.sleep(interval)


if __name__ == "__main__":
    raise SystemExit(main())
