#!/usr/bin/env python3
"""Terminal dashboard for Academic-RAG v2 closure progress.

Shows:
- Active phase/process (raw/rule/llm prepare, retrieval eval, answer eval)
- Milvus entity counts for raw/rule/llm collections
- Output artifact readiness under artifacts/benchmarks/closure_v2

Usage examples:
  /Users/cc/.virtualenvs/scholar-ai-api/bin/python scripts/evals/visualize_closure_progress.py
  /Users/cc/.virtualenvs/scholar-ai-api/bin/python scripts/evals/visualize_closure_progress.py --watch
  /Users/cc/.virtualenvs/scholar-ai-api/bin/python scripts/evals/visualize_closure_progress.py --watch --interval 5
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = ROOT / "artifacts" / "benchmarks" / "closure_v2"

MODES = ("raw", "rule", "llm")
COLLECTIONS = {
    "raw": "paper_contents_v2_qwen_v2_raw",
    "rule": "paper_contents_v2_qwen_v2_rule",
    "llm": "paper_contents_v2_qwen_v2_llm",
}


@dataclass(frozen=True)
class ProcessState:
    pid: str
    command: str
    phase: str


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def detect_processes() -> list[ProcessState]:
    proc = _run([
        "pgrep",
        "-fal",
        "run_academic_rag_v2_closure.sh|prepare_real_retrieval_dataset.py|eval_retrieval.py|eval_answer.py",
    ])
    if proc.returncode != 0:
        return []

    rows: list[ProcessState] = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            pid, command = line.split(" ", 1)
        except ValueError:
            continue
        phase = classify_phase(command)
        rows.append(ProcessState(pid=pid, command=command, phase=phase))
    return rows


def classify_phase(command: str) -> str:
    if "prepare_real_retrieval_dataset.py" in command:
        for mode in MODES:
            marker = f"--contextual-mode {mode}"
            if marker in command:
                return f"prepare:{mode}"
        return "prepare:unknown"
    if "eval_retrieval.py" in command:
        return "eval:retrieval"
    if "eval_answer.py" in command:
        return "eval:answer"
    if "run_academic_rag_v2_closure.sh" in command:
        return "orchestrator"
    return "unknown"


def get_collection_count(name: str) -> Optional[int]:
    try:
        from pymilvus import Collection, connections  # type: ignore
    except Exception:
        return None

    try:
        connections.connect(alias="viz", host="localhost", port=19530)
        collection = Collection(name, using="viz")
        return int(collection.num_entities)
    except Exception:
        return None


def artifact_exists(path: Path) -> bool:
    return path.exists() and path.is_file()


def render_status_icon(ok: bool) -> str:
    return "OK" if ok else "--"


def current_mode(processes: list[ProcessState]) -> str:
    for p in processes:
        if p.phase.startswith("prepare:"):
            return p.phase.replace("prepare:", "")
    for p in processes:
        if p.phase.startswith("eval:"):
            return p.phase.replace("eval:", "")
    return "idle"


def build_report() -> str:
    processes = detect_processes()
    mode_now = current_mode(processes)

    counts = {mode: get_collection_count(COLLECTIONS[mode]) for mode in MODES}

    lines: list[str] = []
    lines.append("Academic-RAG v2 Closure Progress")
    lines.append(f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Current Stage: {mode_now}")
    lines.append("")

    lines.append("Processes:")
    if processes:
        for p in processes:
            lines.append(f"- [{p.phase}] pid={p.pid}")
    else:
        lines.append("- no active closure process")
    lines.append("")

    lines.append("Milvus Entity Counts:")
    for mode in MODES:
        count = counts[mode]
        val = "N/A" if count is None else str(count)
        lines.append(f"- {mode:4s}: {val}")
    lines.append("")

    lines.append("Artifacts:")
    for mode in MODES:
        retrieval_json = OUTPUT_ROOT / mode / f"retrieval_{mode}.json"
        answer_json = OUTPUT_ROOT / mode / f"answer_{mode}.json"
        lines.append(
            f"- {mode:4s}: retrieval={render_status_icon(artifact_exists(retrieval_json))} "
            f"answer={render_status_icon(artifact_exists(answer_json))}"
        )
    report = OUTPUT_ROOT / "closure_report.md"
    lines.append(f"- report: {render_status_icon(artifact_exists(report))}")

    return "\n".join(lines)


def clear_screen() -> None:
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Visualize closure benchmark progress")
    parser.add_argument("--watch", action="store_true", help="Refresh continuously")
    parser.add_argument("--interval", type=int, default=8, help="Refresh interval seconds")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.watch:
        print(build_report())
        return 0

    interval = max(1, int(args.interval))
    while True:
        clear_screen()
        print(build_report())
        print("\nPress Ctrl+C to stop watching.")
        time.sleep(interval)


if __name__ == "__main__":
    raise SystemExit(main())
