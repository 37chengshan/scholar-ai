#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections, utility

from app.core.model_gateway import create_embedding_provider

from scripts.evals.v2_4_common import (
    DEFAULT_ARTIFACT_ROOT,
    DEFAULT_OUTPUT_DIR,
    OFFICIAL_MODEL,
    OFFICIAL_PROVIDER,
    REQUIRED_CHUNK_FIELDS,
    chunk_file_for_stage,
    collect_paper_artifacts,
    infer_ingest_status,
    is_deprecated_output_collection,
    normalize_bool,
    read_json,
    required_field_missing,
    source_chunk_set,
    stage_collection_name,
    write_json,
    write_markdown,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="v2.4 build API flash collections")
    p.add_argument("--artifact-root", default=str(DEFAULT_ARTIFACT_ROOT))
    p.add_argument("--stage", choices=["raw", "rule", "llm", "all"], default="all")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--batch-size", type=int, default=16)
    p.add_argument("--limit-papers", type=int, default=None)
    p.add_argument("--dashboard-interval-seconds", type=int, default=10)
    p.add_argument("--collection-suffix", default="v2_4")
    p.add_argument("--provider", default=OFFICIAL_PROVIDER)
    p.add_argument("--model", default=OFFICIAL_MODEL)
    p.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    p.add_argument("--milvus-host", default="localhost")
    p.add_argument("--milvus-port", type=int, default=19530)
    return p.parse_args()


def stages_from_arg(stage: str) -> List[str]:
    return ["raw", "rule", "llm"] if stage == "all" else [stage]


def ensure_collection_v3(name: str, dim: int, alias: str) -> Collection:
    if is_deprecated_output_collection(name):
        raise RuntimeError(f"deprecated_or_forbidden_output_collection:{name}")

    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="source_chunk_id", dtype=DataType.VARCHAR, max_length=128),
        FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, max_length=192),
        FieldSchema(name="paper_id", dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name="user_id", dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name="parse_id", dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name="page_num", dtype=DataType.INT64),
        FieldSchema(name="content_type", dtype=DataType.VARCHAR, max_length=32),
        FieldSchema(name="section", dtype=DataType.VARCHAR, max_length=512),
        FieldSchema(name="normalized_section_path", dtype=DataType.VARCHAR, max_length=512),
        FieldSchema(name="anchor_text", dtype=DataType.VARCHAR, max_length=1024),
        FieldSchema(name="char_start", dtype=DataType.INT64),
        FieldSchema(name="char_end", dtype=DataType.INT64),
        FieldSchema(name="stage", dtype=DataType.VARCHAR, max_length=16),
        FieldSchema(name="indexable", dtype=DataType.BOOL),
        FieldSchema(name="embedding_status", dtype=DataType.VARCHAR, max_length=32),
        FieldSchema(name="content_data", dtype=DataType.VARCHAR, max_length=65535),
        FieldSchema(name="raw_data", dtype=DataType.JSON),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim),
    ]

    if not utility.has_collection(name, using=alias):
        schema = CollectionSchema(fields=fields, description="ScholarAI v2.4 API flash schema v3", enable_dynamic_field=True)
        col = Collection(name=name, schema=schema, using=alias)
        col.create_index(
            field_name="embedding",
            index_params={"index_type": "IVF_FLAT", "metric_type": "COSINE", "params": {"nlist": 128}},
        )
        col.load()
        return col

    col = Collection(name=name, using=alias)
    col.load()
    # hard gate dim mismatch
    got_dim = 0
    for f in col.schema.fields:
        if f.name == "embedding":
            got_dim = int((f.params or {}).get("dim", 0))
            break
    if got_dim != dim:
        raise RuntimeError(f"collection_dim_mismatch:{name}:{got_dim}!={dim}")
    return col


def _dashboard_base(args: argparse.Namespace, dim: int, probe_status: str) -> Dict[str, Any]:
    return {
        "title": "ScholarAI API Flash v2.4 Ingestion Dashboard",
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "provider": {
            "provider": args.provider,
            "model": args.model,
            "dimension": dim,
            "probe": probe_status,
        },
        "artifacts": {
            "papers_loaded": 0,
            "parse_artifacts": "0/0",
            "raw_chunks": 0,
            "rule_chunks": 0,
            "llm_chunks": 0,
            "source_chunk_id_alignment": "PENDING",
        },
        "stages": {
            "build:raw": "PENDING",
            "build:rule": "PENDING",
            "build:llm": "PENDING",
        },
        "current": {
            "paper": "",
            "stage": "",
            "chunks_embedded": "0/0",
            "chunks_inserted": "0/0",
            "failed": 0,
            "speed_chunks_per_min": 0.0,
            "eta": "00:00:00",
        },
        "collections": {},
        "recent_errors": [],
    }


def _ensure_probe_pass(output_dir: Path) -> Tuple[str, int]:
    probe_path = output_dir / "provider_probe.json"
    if not probe_path.exists():
        raise RuntimeError("provider_probe_missing")
    probe = read_json(probe_path)
    status = str(probe.get("status") or "BLOCKED")
    dim = int(probe.get("dimension") or 0)
    if status != "PASS" or dim <= 0:
        raise RuntimeError(f"provider_probe_blocked:{status}:dim={dim}")
    return status, dim


def _load_stage_chunks(artifact_root: Path, stage: str, limit_papers: Optional[int]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    papers = collect_paper_artifacts(artifact_root, limit_papers)
    if not papers:
        raise RuntimeError(f"INGEST_BLOCKED:artifact_root_missing_or_empty:{artifact_root}")
    parse_ok = 0
    rows: List[Dict[str, Any]] = []
    source_sets: List[Set[str]] = []
    per_stage_counts = {"raw": 0, "rule": 0, "llm": 0}

    for paper in papers:
        if not paper.parse_artifact_path.exists():
            raise RuntimeError(f"INGEST_BLOCKED:missing_parse_artifact:{paper.paper_id}")
        parse_ok += 1

        stage_chunks: Dict[str, List[Dict[str, Any]]] = {}
        for s in ["raw", "rule", "llm"]:
            path = chunk_file_for_stage(paper, s)
            if not path.exists():
                raise RuntimeError(f"INGEST_BLOCKED:missing_chunks_{s}:{paper.paper_id}")
            content = list(read_json(path) or [])
            stage_chunks[s] = content
            per_stage_counts[s] += len(content)

        raw_set = source_chunk_set(stage_chunks["raw"])
        if raw_set != source_chunk_set(stage_chunks["rule"]) or raw_set != source_chunk_set(stage_chunks["llm"]):
            raise RuntimeError(f"INGEST_BLOCKED:source_chunk_id_misaligned:{paper.paper_id}")
        source_sets.append(raw_set)

        for chunk in stage_chunks[stage]:
            missing = required_field_missing(chunk, REQUIRED_CHUNK_FIELDS)
            if missing:
                raise RuntimeError(
                    f"INGEST_BLOCKED:missing_fields:{paper.paper_id}:{stage}:{','.join(sorted(set(missing)))}"
                )
            if str(chunk.get("stage") or "") != stage:
                raise RuntimeError(f"INGEST_BLOCKED:stage_mismatch:{paper.paper_id}:{stage}")

            record = {
                "source_chunk_id": str(chunk["source_chunk_id"]),
                "chunk_id": str(chunk["chunk_id"]),
                "paper_id": str(chunk["paper_id"]),
                "user_id": str(chunk.get("user_id") or "benchmark-user"),
                "parse_id": str(chunk["parse_id"]),
                "page_num": int(chunk["page_num"]),
                "content_type": str(chunk["content_type"]),
                "section": str(chunk.get("section_path") or ""),
                "normalized_section_path": str(chunk.get("normalized_section_path") or ""),
                "anchor_text": str(chunk.get("anchor_text") or ""),
                "char_start": int(chunk["char_start"]),
                "char_end": int(chunk["char_end"]),
                "stage": stage,
                "indexable": normalize_bool(chunk.get("indexable")),
                "embedding_status": "pending",
                "content_data": str(chunk["content_data"]),
                "raw_data": {
                    "parent_source_chunk_id": chunk.get("parent_source_chunk_id"),
                    "warnings": chunk.get("warnings", []),
                },
            }
            rows.append(record)

    # Global uniqueness check: no source_chunk_id should appear in more than one paper.
    # (The previous equality check incorrectly required all papers to have identical chunk sets.)
    all_ids: Set[str] = set()
    total_expected = sum(len(s) for s in source_sets)
    for s in source_sets:
        all_ids |= s
    alignment_ok = len(all_ids) == total_expected
    if not alignment_ok:
        raise RuntimeError("INGEST_BLOCKED:global_source_chunk_id_misaligned")

    stats = {
        "papers_loaded": len(papers),
        "parse_artifacts": f"{parse_ok}/{len(papers)}",
        "raw_chunks": per_stage_counts["raw"],
        "rule_chunks": per_stage_counts["rule"],
        "llm_chunks": per_stage_counts["llm"],
        "source_chunk_id_alignment": "PASS" if alignment_ok else "BLOCKED",
    }
    return rows, stats


def _chunk_records(records: List[Dict[str, Any]], size: int) -> List[List[Dict[str, Any]]]:
    return [records[i:i + size] for i in range(0, len(records), size)]


def _stage_key(stage: str) -> str:
    return f"build:{stage}"


def _write_dashboard_md(path: Path, payload: Dict[str, Any]) -> None:
    provider = payload.get("provider") or {}
    artifacts = payload.get("artifacts") or {}
    stages = payload.get("stages") or {}
    lines = [
        f"Updated: {payload.get('updated')}",
        "",
        "## Provider",
        f"- provider: {provider.get('provider', 'unknown')}",
        f"- model: {provider.get('model', 'unknown')}",
        f"- dimension: {provider.get('dimension', 0)}",
        f"- probe: {provider.get('probe', 'BLOCKED')}",
        "",
        "## Artifacts",
        f"- papers_loaded: {artifacts.get('papers_loaded', 0)}",
        f"- parse_artifacts: {artifacts.get('parse_artifacts', '0/0')}",
        f"- raw_chunks: {artifacts.get('raw_chunks', 0)}",
        f"- rule_chunks: {artifacts.get('rule_chunks', 0)}",
        f"- llm_chunks: {artifacts.get('llm_chunks', 0)}",
        f"- source_chunk_id_alignment: {artifacts.get('source_chunk_id_alignment', 'BLOCKED')}",
        "",
        "## Stage Status",
        f"- build:raw: {stages.get('build:raw', 'PENDING')}",
        f"- build:rule: {stages.get('build:rule', 'PENDING')}",
        f"- build:llm: {stages.get('build:llm', 'PENDING')}",
        "",
        "## Collections",
    ]
    for stage, stat in payload.get("collections", {}).items():
        lines.append(f"- {stage}: {stat}")
    lines.append("")
    lines.append("## Recent Errors")
    errors = payload.get("recent_errors") or ["none"]
    for item in errors:
        lines.append(f"- {item}")
    write_markdown(path, payload.get("title", "v2.4 Ingestion Dashboard"), lines)


def main() -> int:
    args = parse_args()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    stages = stages_from_arg(args.stage)
    alias = "v24_ingest"

    connections.connect(alias=alias, host=args.milvus_host, port=args.milvus_port)

    report: Dict[str, Any] = {
        "provider": args.provider,
        "model": args.model,
        "stage": args.stage,
        "collection_suffix": args.collection_suffix,
        "dry_run": args.dry_run,
        "resume": args.resume,
        "stages": {},
        "failed_source_chunk_ids": [],
        "fallback_used": False,
        "deprecated_branch_used": False,
        "status": "BLOCKED",
        "error": None,
    }

    try:
        probe_status, dim = _ensure_probe_pass(out_dir)
        provider = create_embedding_provider(args.provider, args.model)
        if int(provider.dimension()) != dim:
            raise RuntimeError(f"provider_dimension_probe_mismatch:{provider.dimension()}!={dim}")

        dashboard = _dashboard_base(args, dim=dim, probe_status=probe_status)
        write_json(out_dir / "api_flash_ingest_dashboard.json", dashboard)
        _write_dashboard_md(out_dir / "api_flash_ingest_dashboard.md", dashboard)

        global_errors: List[str] = []
        last_dashboard_flush = time.time()

        for stage in ["raw", "rule", "llm"]:
            dashboard["stages"][_stage_key(stage)] = "PENDING"

        for stage in stages:
            stage_collection = stage_collection_name(stage, args.collection_suffix)
            col = ensure_collection_v3(stage_collection, dim=dim, alias=alias)

            rows, artifact_stats = _load_stage_chunks(Path(args.artifact_root), stage, args.limit_papers)
            dashboard["artifacts"].update(artifact_stats)
            dashboard["stages"][_stage_key(stage)] = "RUNNING"
            dashboard["collections"][stage] = f"0/{len(rows)} | {stage_collection}"

            existing_source_ids: Set[str] = set()
            if args.resume and not args.dry_run:
                existed = col.query(expr="id >= 0", output_fields=["source_chunk_id"], limit=16384)
                existing_source_ids = {str(r.get("source_chunk_id") or "") for r in existed if str(r.get("source_chunk_id") or "")}

            rows_to_process = [r for r in rows if str(r["source_chunk_id"]) not in existing_source_ids]
            expected_count = len(rows) if not args.resume else len(existing_source_ids) + len(rows_to_process)

            inserted = 0
            failed = 0
            started = time.time()

            for batch in _chunk_records(rows_to_process, args.batch_size):
                texts = [str(r["content_data"]) for r in batch]
                try:
                    vectors = provider.embed_texts(texts)
                except Exception as exc:
                    for r in batch:
                        report["failed_source_chunk_ids"].append(str(r["source_chunk_id"]))
                    failed += len(batch)
                    global_errors.append(f"embedding_failed:{stage}:{exc}")
                    continue

                if len(vectors) != len(batch):
                    for r in batch:
                        report["failed_source_chunk_ids"].append(str(r["source_chunk_id"]))
                    failed += len(batch)
                    global_errors.append(f"embedding_count_mismatch:{stage}:{len(vectors)}!={len(batch)}")
                    continue

                if not args.dry_run:
                    entities: List[Dict[str, Any]] = []
                    for r, vec in zip(batch, vectors):
                        entities.append(
                            {
                                **r,
                                "embedding_status": "embedded",
                                "embedding": vec,
                            }
                        )
                    col.insert(entities)
                    inserted += len(entities)
                else:
                    inserted += len(batch)

                now = time.time()
                elapsed_min = max((now - started) / 60.0, 1e-6)
                speed = inserted / elapsed_min
                remain = max(len(rows_to_process) - inserted, 0)
                eta_min = remain / speed if speed > 0 else 0.0
                eta_sec = int(eta_min * 60)
                dashboard["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                dashboard["current"] = {
                    "paper": "rolling",
                    "stage": stage,
                    "chunks_embedded": f"{inserted}/{len(rows_to_process)}",
                    "chunks_inserted": f"{inserted}/{len(rows_to_process)}",
                    "failed": failed,
                    "speed_chunks_per_min": round(speed, 3),
                    "eta": f"{eta_sec // 3600:02d}:{(eta_sec % 3600) // 60:02d}:{eta_sec % 60:02d}",
                }
                dashboard["collections"][stage] = f"{inserted}/{len(rows_to_process)} | {stage_collection}"

                if now - last_dashboard_flush >= args.dashboard_interval_seconds:
                    write_json(out_dir / "api_flash_ingest_dashboard.json", dashboard)
                    _write_dashboard_md(out_dir / "api_flash_ingest_dashboard.md", dashboard)
                    last_dashboard_flush = now

            if not args.dry_run:
                col.flush()
            final_count = expected_count if args.dry_run else col.num_entities

            stage_errors: List[str] = []
            if failed > 0:
                stage_errors.append(f"failed_count_gt_zero:{failed}")
            if final_count != expected_count:
                stage_errors.append(f"entity_count_mismatch:{final_count}!={expected_count}")

            status = infer_ingest_status(stage_errors)
            if stage_errors:
                global_errors.extend([f"{stage}:{e}" for e in stage_errors])

            dashboard["stages"][_stage_key(stage)] = "PASS" if status == "PASS" else "BLOCKED"
            dashboard["collections"][stage] = f"{final_count}/{expected_count} | {stage_collection}"

            report["stages"][stage] = {
                "collection": stage_collection,
                "expected_count": expected_count,
                "final_count": final_count,
                "processed": len(rows_to_process),
                "inserted": inserted,
                "failed": failed,
                "status": status,
                "errors": stage_errors,
            }

        report["status"] = infer_ingest_status(global_errors)
        dashboard["recent_errors"] = global_errors[-20:] if global_errors else ["none"]
        dashboard["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    except Exception as exc:
        report["status"] = "BLOCKED"
        report["error"] = str(exc)
        dashboard = _dashboard_base(args, dim=0, probe_status="BLOCKED")
        dashboard["recent_errors"] = [str(exc)]
        dashboard["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    write_json(out_dir / "api_flash_ingest_dashboard.json", dashboard)
    _write_dashboard_md(out_dir / "api_flash_ingest_dashboard.md", dashboard)
    write_json(out_dir / "api_flash_ingest_report.json", report)
    if args.dry_run:
        write_json(out_dir / "api_flash_ingest_report_dry_run.json", report)
        write_json(out_dir / "api_flash_ingest_dashboard_dry_run.json", dashboard)

    report_lines = [
        f"- provider: {report['provider']}",
        f"- model: {report['model']}",
        f"- dry_run: {report['dry_run']}",
        f"- resume: {report['resume']}",
        f"- fallback_used: {report['fallback_used']}",
        f"- deprecated_branch_used: {report['deprecated_branch_used']}",
        f"- status: {report['status']}",
        "",
        "## Stage Status",
    ]
    for stage, stat in report.get("stages", {}).items():
        report_lines.append(
            f"- {stage}: {stat.get('status')} ({stat.get('final_count')}/{stat.get('expected_count')})"
        )
        if stat.get("errors"):
            for err in stat["errors"]:
                report_lines.append(f"  - {err}")
    if report.get("error"):
        report_lines.extend(["", "## Error", "", "```", str(report["error"]), "```"])
    write_markdown(out_dir / "api_flash_ingest_report.md", "v2.4 API Flash Ingest Report", report_lines)
    if args.dry_run:
        write_markdown(out_dir / "api_flash_ingest_report_dry_run.md", "v2.4 API Flash Ingest Dry Run Report", report_lines)
        _write_dashboard_md(out_dir / "api_flash_ingest_dashboard_dry_run.md", dashboard)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
