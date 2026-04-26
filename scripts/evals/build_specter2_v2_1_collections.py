#!/usr/bin/env python3
"""SPECTER2 v2.1 Collection Builder — Visualized Ingestion Script.

Builds raw/rule/llm Milvus collections for SPECTER2 scientific dense line,
using the same 20-paper, 1451-chunk dataset as Qwen v2.1 collections.

Usage:
  python scripts/evals/build_specter2_v2_1_collections.py --dataset-profile v2.1 --stage all
  python scripts/evals/build_specter2_v2_1_collections.py --stage raw --resume
  python scripts/evals/build_specter2_v2_1_collections.py --dry-run

Output:
  artifacts/benchmarks/specter2_v2_1_20/specter2_ingest_dashboard.json
  artifacts/benchmarks/specter2_v2_1_20/specter2_ingest_dashboard.md
  artifacts/benchmarks/specter2_v2_1_20/specter2_ingest_report.json
  artifacts/benchmarks/specter2_v2_1_20/specter2_ingest_report.md
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parent.parent.parent
API_ROOT = ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

OUT_DIR = ROOT / "artifacts/benchmarks/specter2_v2_1_20"
RAW_CHUNKS_PATH = ROOT / "artifacts/benchmarks/v2.1/raw_base/raw_chunks.jsonl"
MANIFEST_PATH = ROOT / "artifacts/benchmarks/v2.1/raw_base/raw_chunks_manifest.json"

SPECTER2_DIM = 768
EXPECTED_CHUNK_COUNT = 1451
EXPECTED_PAPER_COUNT = 20

SPECTER2_COLLECTIONS = {
    "raw": "paper_contents_v2_specter2_raw_v2_1",
    "rule": "paper_contents_v2_specter2_rule_v2_1",
    "llm": "paper_contents_v2_specter2_llm_v2_1",
}

RESUME_FILE = OUT_DIR / "specter2_ingest_resume.json"
DASHBOARD_JSON = OUT_DIR / "specter2_ingest_dashboard.json"
DASHBOARD_MD = OUT_DIR / "specter2_ingest_dashboard.md"


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_raw_chunks() -> list[dict]:
    chunks = []
    with open(RAW_CHUNKS_PATH) as f:
        for line in f:
            line = line.strip()
            if line:
                chunks.append(json.loads(line))
    return chunks


def apply_rule_stage(chunk: dict) -> dict:
    """Rule-based chunk transformation: clean whitespace, section normalization."""
    text = str(chunk.get("raw_chunk_text") or "").strip()
    # Collapse multiple spaces/newlines
    import re
    text = re.sub(r"\s{3,}", "  ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return {**chunk, "content_data": text}


def apply_llm_stage(chunk: dict, llm_prefix_cache: dict) -> dict:
    """LLM-enriched chunk: prepend contextual prefix from cache if available."""
    raw_text = str(chunk.get("raw_chunk_text") or "").strip()
    cid = chunk.get("source_chunk_id", "")
    prefix = llm_prefix_cache.get(cid, "")
    content = f"{prefix}\n\n{raw_text}".strip() if prefix else raw_text
    return {**chunk, "content_data": content}


def get_content_data_for_stage(chunk: dict, stage: str, llm_cache: dict) -> str:
    if stage == "raw":
        return str(chunk.get("raw_chunk_text") or "").strip()
    elif stage == "rule":
        return apply_rule_stage(chunk)["content_data"]
    elif stage == "llm":
        return apply_llm_stage(chunk, llm_cache)["content_data"]
    return str(chunk.get("raw_chunk_text") or "").strip()


# ── Collection creation ────────────────────────────────────────────────────────

def create_specter2_collection(
    svc: Any, collection_name: str, dim: int = SPECTER2_DIM, drop_if_empty: bool = False
) -> Any:
    """Create a SPECTER2 collection with the required schema."""
    from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, utility

    if utility.has_collection(collection_name, using=svc._alias):
        col = Collection(collection_name, using=svc._alias)
        col.load()
        # Drop and recreate if empty and caller requests it (fresh non-resume run)
        if drop_if_empty and col.num_entities == 0:
            print(f"  Dropping empty collection {collection_name} for fresh build...")
            utility.drop_collection(collection_name, using=svc._alias)
        else:
            print(f"  Collection {collection_name} exists ({col.num_entities} entities), reusing.")
            return col

    print(f"  Creating collection {collection_name} (dim={dim})...")
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="source_chunk_id", dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name="paper_id", dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name="user_id", dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name="page_num", dtype=DataType.INT64),
        FieldSchema(name="section", dtype=DataType.VARCHAR, max_length=256),
        FieldSchema(name="content_type", dtype=DataType.VARCHAR, max_length=32),
        FieldSchema(name="content_data", dtype=DataType.VARCHAR, max_length=32000),
        FieldSchema(name="stage", dtype=DataType.VARCHAR, max_length=16),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim),
    ]
    schema = CollectionSchema(fields, f"SPECTER2 embeddings for {collection_name}")
    col = Collection(collection_name, schema, using=svc._alias)
    index_params = {
        "metric_type": "COSINE",
        "index_type": "IVF_FLAT",
        "params": {"nlist": 128},
    }
    col.create_index("embedding", index_params)
    col.load()
    print(f"  Created: {collection_name}")
    return col


# ── Progress tracking ─────────────────────────────────────────────────────────

class StageProgress:
    def __init__(self, stage: str, total: int):
        self.stage = stage
        self.total = total
        self.done = 0
        self.failed = 0
        self.start_time = time.time()
        self.status = "PENDING"  # PENDING / RUNNING / DONE / FAILED

    def to_dict(self) -> dict:
        elapsed = time.time() - self.start_time
        speed = (self.done / elapsed * 60) if elapsed > 0 and self.done > 0 else 0
        remaining = max(0, self.total - self.done)
        eta_s = int(remaining / (self.done / elapsed)) if self.done > 0 and elapsed > 0 else 0
        h, r = divmod(eta_s, 3600)
        m, s = divmod(r, 60)
        return {
            "stage": self.stage,
            "total": self.total,
            "done": self.done,
            "failed": self.failed,
            "status": self.status,
            "speed_chunks_per_min": round(speed, 1),
            "eta": f"{h:02d}:{m:02d}:{s:02d}",
            "collection": SPECTER2_COLLECTIONS[self.stage],
        }


# ── Dashboard ─────────────────────────────────────────────────────────────────

def render_dashboard(stages: dict[str, StageProgress], current_stage: str, interval: float):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "ScholarAI SPECTER2 v2.1 Ingestion Dashboard",
        f"Updated: {now}",
        "",
        "Manifest:",
        f"  expected_papers: {EXPECTED_PAPER_COUNT}",
        f"  total_chunks: {EXPECTED_CHUNK_COUNT}",
        "",
        "Stages:",
    ]
    for stage_name, prog in stages.items():
        status_sym = {
            "PENDING": "PENDING",
            "RUNNING": "RUNNING",
            "DONE": "DONE",
            "FAILED": "FAILED",
        }.get(prog.status, prog.status)
        lines.append(f"  build:{stage_name:4s} : {status_sym}")

    if current_stage and current_stage in stages:
        prog = stages[current_stage]
        d = prog.to_dict()
        lines += [
            "",
            "Current Stage:",
            f"  stage: {current_stage}",
            f"  chunks: {d['done']}/{d['total']}",
            f"  failed: {d['failed']}",
            f"  speed: {d['speed_chunks_per_min']} chunks/min",
            f"  eta: {d['eta']}",
        ]

    lines += ["", "Collections:"]
    for stage_name, prog in stages.items():
        d = prog.to_dict()
        lines.append(
            f"  {stage_name:4s}: {d['done']:4d}/{d['total']:4d} | {d['collection']}"
        )

    lines.append(f"\nPress Ctrl+C to stop.\n")
    print("\033[2J\033[H" + "\n".join(lines), end="", flush=True)

    # Write dashboard files
    dashboard = {
        "generated_at": now,
        "stages": {k: v.to_dict() for k, v in stages.items()},
    }
    DASHBOARD_JSON.write_text(json.dumps(dashboard, indent=2))
    md_content = "# SPECTER2 Ingestion Dashboard\n\n```\n" + "\n".join(lines) + "\n```\n"
    DASHBOARD_MD.write_text(md_content)


# ── Load resume state ─────────────────────────────────────────────────────────

def load_resume(stage: str) -> set[str]:
    """Load already-inserted source_chunk_ids for a stage from resume file."""
    if not RESUME_FILE.exists():
        return set()
    try:
        data = json.loads(RESUME_FILE.read_text())
        return set(data.get(stage, []))
    except Exception:
        return set()


def save_resume(stage: str, inserted_ids: set[str]) -> None:
    existing = {}
    if RESUME_FILE.exists():
        try:
            existing = json.loads(RESUME_FILE.read_text())
        except Exception:
            pass
    existing[stage] = list(inserted_ids)
    RESUME_FILE.write_text(json.dumps(existing, indent=2))


# ── Build a single stage ──────────────────────────────────────────────────────

def build_stage(
    stage: str,
    chunks: list[dict],
    svc_milvus: Any,
    svc_embed: Any,
    prog: StageProgress,
    stages: dict[str, StageProgress],
    batch_size: int,
    resume: bool,
    dry_run: bool,
    dashboard_interval: float,
    llm_cache: dict,
) -> tuple[bool, list[str]]:
    """Build embeddings + insert for one stage. Returns (success, failed_ids)."""
    collection_name = SPECTER2_COLLECTIONS[stage]
    failed_ids = []
    inserted_ids = set()

    if not dry_run:
        col = create_specter2_collection(
            svc_milvus, collection_name, SPECTER2_DIM, drop_if_empty=not resume
        )
    else:
        col = None
        print(f"  [DRY-RUN] Would create {collection_name}")

    # Resume
    if resume:
        inserted_ids = load_resume(stage)
        prog.done = len(inserted_ids)
        print(f"  [RESUME] {stage}: already done {len(inserted_ids)} chunks")

    # Skip already-done
    todo = [c for c in chunks if c.get("source_chunk_id", "") not in inserted_ids]
    print(f"  {stage}: {len(todo)} chunks to process")

    prog.status = "RUNNING"
    last_dashboard = time.time()

    for i in range(0, len(todo), batch_size):
        batch = todo[i : i + batch_size]

        # Build content_data per stage
        texts = []
        for chunk in batch:
            cd = get_content_data_for_stage(chunk, stage, llm_cache)
            texts.append(cd or str(chunk.get("raw_chunk_text") or ""))

        # Embed
        try:
            embeddings = svc_embed.generate_embeddings_batch(texts, batch_size=batch_size)
        except Exception as e:
            for chunk in batch:
                failed_ids.append(chunk.get("source_chunk_id", "?"))
                prog.failed += 1
            print(f"  [EMBED ERROR] batch {i//batch_size}: {e}", file=sys.stderr)
            continue

        # Build records
        records = []
        for j, chunk in enumerate(batch):
            vec = embeddings[j] if j < len(embeddings) else None
            if not vec or len(vec) != SPECTER2_DIM:
                failed_ids.append(chunk.get("source_chunk_id", "?"))
                prog.failed += 1
                continue

            content_data = texts[j][:31000]  # max_length=32000 in schema
            records.append({
                "source_chunk_id": chunk.get("source_chunk_id", "")[:64],
                "paper_id": chunk.get("paper_id", "")[:64],
                "user_id": (chunk.get("user_id") or "")[:64],
                "page_num": int(chunk.get("page_num") or 0),
                "section": str(chunk.get("section_path") or chunk.get("subsection") or "")[:255],
                "content_type": str(chunk.get("content_type") or "text")[:31],
                "content_data": content_data,
                "stage": stage[:15],
                "embedding": vec,
            })

        if records and not dry_run:
            try:
                col.insert(records)  # list-of-dicts row format
                for r in records:
                    inserted_ids.add(r["source_chunk_id"])
                    prog.done += 1
            except Exception as e:
                for r in records:
                    failed_ids.append(r["source_chunk_id"])
                    prog.failed += 1
                print(f"  [INSERT ERROR] batch {i//batch_size}: {e}", file=sys.stderr)
        elif records and dry_run:
            for r in records:
                inserted_ids.add(r["source_chunk_id"])
                prog.done += 1

        # Dashboard refresh
        if time.time() - last_dashboard >= dashboard_interval:
            render_dashboard(stages, stage, dashboard_interval)
            if resume:
                save_resume(stage, inserted_ids)
            last_dashboard = time.time()

    # Final flush
    if not dry_run and col:
        col.flush()
        count = col.num_entities
        print(f"\n  {stage} inserted: {count}/{EXPECTED_CHUNK_COUNT}")
        if count != EXPECTED_CHUNK_COUNT and not failed_ids:
            pass  # may be resume partial

    if resume:
        save_resume(stage, inserted_ids)

    if failed_ids:
        prog.status = "FAILED"
        return False, failed_ids

    prog.status = "DONE"
    return True, []


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Build SPECTER2 v2.1 collections")
    parser.add_argument("--dataset-profile", default="v2.1")
    parser.add_argument("--manifest", default=str(MANIFEST_PATH))
    parser.add_argument("--stage", choices=["raw", "rule", "llm", "all"], default="all")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit-papers", type=int, default=0)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--dashboard-interval-seconds", type=float, default=5.0)
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("ScholarAI SPECTER2 v2.1 Ingestion")
    print("=" * 60)

    if args.dry_run:
        print("  [DRY-RUN] No Milvus writes will be performed.")

    # -- Load raw chunks --
    print(f"\nLoading raw chunks from {RAW_CHUNKS_PATH} ...")
    all_chunks = load_raw_chunks()
    print(f"  Loaded {len(all_chunks)} chunks")

    if args.limit_papers > 0:
        paper_ids_limit = sorted({c["paper_id"] for c in all_chunks})[: args.limit_papers]
        all_chunks = [c for c in all_chunks if c["paper_id"] in set(paper_ids_limit)]
        print(f"  Limited to {args.limit_papers} papers: {len(all_chunks)} chunks")

    # -- Load SPECTER2 model --
    print("\nLoading SPECTER2 model...")
    from app.core.specter2_embedding_service import Specter2EmbeddingService

    svc_embed = Specter2EmbeddingService(adapter="proximity")
    svc_embed._load_model()
    actual_dim = len(svc_embed.generate_embedding("test"))
    print(f"  SPECTER2 loaded, dim={actual_dim}")
    assert actual_dim == SPECTER2_DIM, f"dim mismatch: {actual_dim} != {SPECTER2_DIM}"

    # -- Connect Milvus --
    svc_milvus = None
    if not args.dry_run:
        from app.core.milvus_service import get_milvus_service
        svc_milvus = get_milvus_service()
        svc_milvus.connect()
        print(f"  Milvus connected (alias={svc_milvus._alias})")

    # -- Determine stages to build --
    if args.stage == "all":
        stages_to_build = ["raw", "rule", "llm"]
    else:
        stages_to_build = [args.stage]

    # -- Initialize progress --
    all_stage_progress: dict[str, StageProgress] = {
        s: StageProgress(s, len(all_chunks)) for s in ["raw", "rule", "llm"]
    }
    for s in stages_to_build:
        all_stage_progress[s].status = "RUNNING" if s == stages_to_build[0] else "PENDING"

    # LLM contextual prefix cache (load from variant timing if available)
    llm_cache: dict[str, str] = {}

    # -- Build each stage --
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset_profile": args.dataset_profile,
        "dry_run": args.dry_run,
        "embedding_model": svc_embed.BASE_MODEL,
        "embedding_dim": actual_dim,
        "expected_chunks": EXPECTED_CHUNK_COUNT,
        "stages": {},
        "status": "BLOCKED",
        "blocked_reason": "",
    }

    all_ok = True
    for stage in stages_to_build:
        print(f"\n{'='*60}")
        print(f"  PHASE: build:{stage}")
        print(f"{'='*60}")
        all_stage_progress[stage].status = "RUNNING"
        render_dashboard(all_stage_progress, stage, args.dashboard_interval_seconds)

        ok, failed = build_stage(
            stage=stage,
            chunks=all_chunks,
            svc_milvus=svc_milvus,
            svc_embed=svc_embed,
            prog=all_stage_progress[stage],
            stages=all_stage_progress,
            batch_size=args.batch_size,
            resume=args.resume,
            dry_run=args.dry_run,
            dashboard_interval=args.dashboard_interval_seconds,
            llm_cache=llm_cache,
        )

        report["stages"][stage] = {
            **all_stage_progress[stage].to_dict(),
            "failed_chunk_ids": failed[:20],  # truncate for report
        }

        if not ok:
            all_ok = False
            report["blocked_reason"] = (
                f"Stage '{stage}' failed: {len(failed)} chunks. "
                f"First few: {failed[:5]}"
            )

    render_dashboard(all_stage_progress, "", args.dashboard_interval_seconds)

    # -- Verify counts --
    if not args.dry_run and svc_milvus:
        from pymilvus import Collection, utility

        print("\nVerifying collection counts...")
        for stage in stages_to_build:
            col_name = SPECTER2_COLLECTIONS[stage]
            if utility.has_collection(col_name, using=svc_milvus._alias):
                col = Collection(col_name, using=svc_milvus._alias)
                count = col.num_entities
                print(f"  {stage}: {count}/{EXPECTED_CHUNK_COUNT}")
                report["stages"][stage]["final_count"] = count
                if count != EXPECTED_CHUNK_COUNT and args.limit_papers == 0:
                    all_ok = False
                    report["blocked_reason"] = (
                        f"Stage '{stage}' count mismatch: {count} != {EXPECTED_CHUNK_COUNT}"
                    )

    report["status"] = "PASS" if all_ok else "BLOCKED"

    # Write report
    report_json = OUT_DIR / "specter2_ingest_report.json"
    report_json.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\n  → {report_json.relative_to(ROOT)}")

    _write_report_md(report)

    status = "✓ PASS" if all_ok else "✗ BLOCKED"
    print(f"\n[{report['status']}] SPECTER2 ingestion: {status}")
    if report.get("blocked_reason"):
        print(f"  Reason: {report['blocked_reason']}")

    return 0 if all_ok else 1


def _write_report_md(report: dict) -> None:
    md_lines = [
        "# SPECTER2 v2.1 Ingestion Report",
        f"\n**Generated:** {report['generated_at']}",
        f"\n**Status:** `{report['status']}`",
        "",
        "## Configuration",
        "",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| dataset_profile | {report['dataset_profile']} |",
        f"| embedding_model | {report['embedding_model']} |",
        f"| embedding_dim | {report['embedding_dim']} |",
        f"| expected_chunks | {report['expected_chunks']} |",
        f"| dry_run | {report['dry_run']} |",
        "",
        "## Stage Results",
        "",
    ]
    for stage, info in report.get("stages", {}).items():
        md_lines += [
            f"### {stage}",
            "",
            f"| Field | Value |",
            f"|-------|-------|",
        ]
        for k, v in info.items():
            if k not in ("failed_chunk_ids",):
                md_lines.append(f"| {k} | {v} |")
        md_lines.append("")

    if report.get("blocked_reason"):
        md_lines += ["## BLOCKED Reason", "", f"> {report['blocked_reason']}", ""]

    md_path = OUT_DIR / "specter2_ingest_report.md"
    md_path.write_text("\n".join(md_lines))
    print(f"  → {md_path.relative_to(ROOT)}")


if __name__ == "__main__":
    sys.exit(main())
