#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[2]
API_ROOT = ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections, utility

from app.core.model_gateway import ProviderDimensionMismatch, create_embedding_provider

SOURCE_COLLECTIONS = {
    "raw": "paper_contents_v2_qwen_v2_raw_v2_1",
    "rule": "paper_contents_v2_qwen_v2_rule_v2_1",
    "llm": "paper_contents_v2_qwen_v2_llm_v2_1",
}
TARGET_COLLECTIONS_FLASH = {
    "raw": "paper_contents_v2_api_tongyi_flash_raw_v2_3",
    "rule": "paper_contents_v2_api_tongyi_flash_rule_v2_3",
    "llm": "paper_contents_v2_api_tongyi_flash_llm_v2_3",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="v2.3 build api embeddings")
    p.add_argument("--provider", default="tongyi")
    p.add_argument("--model", default="tongyi-embedding-vision-flash-2026-03-06")
    p.add_argument("--stage", choices=["raw", "rule", "llm", "all"], default="all")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--batch-size", type=int, default=16)
    p.add_argument("--dashboard-interval-seconds", type=int, default=10)
    p.add_argument("--output-dir", default=str(ROOT / "artifacts" / "benchmarks" / "v2_3"))
    p.add_argument("--milvus-host", default="localhost")
    p.add_argument("--milvus-port", type=int, default=19530)
    return p.parse_args()


def stages_from_arg(stage: str) -> List[str]:
    return ["raw", "rule", "llm"] if stage == "all" else [stage]


def make_schema(dim: int) -> CollectionSchema:
    return CollectionSchema(
        fields=[
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="source_chunk_id", dtype=DataType.VARCHAR, max_length=128),
            FieldSchema(name="paper_id", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="user_id", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="page_num", dtype=DataType.INT64),
            FieldSchema(name="section", dtype=DataType.VARCHAR, max_length=256),
            FieldSchema(name="content_type", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="content_data", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="stage", dtype=DataType.VARCHAR, max_length=16),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim),
        ],
        description="v2.3 api flash embeddings",
        enable_dynamic_field=True,
    )


def ensure_target_collection(name: str, dim: int, alias: str) -> Collection:
    if not utility.has_collection(name, using=alias):
        col = Collection(name=name, schema=make_schema(dim), using=alias)
        col.create_index(field_name="embedding", index_params={"index_type": "IVF_FLAT", "metric_type": "COSINE", "params": {"nlist": 1024}})
        return col

    col = Collection(name=name, using=alias)
    for field in col.schema.fields:
        if field.name == "embedding":
            got_dim = int(field.params.get("dim", 0))
            if got_dim != dim:
                raise ProviderDimensionMismatch(f"collection {name} dim={got_dim}, provider dim={dim}")
            break
    return col


def fetch_source_rows(source: Collection, expected_count: int = 1451) -> List[Dict[str, Any]]:
    rows = source.query(
        expr="id >= 0",
        output_fields=["id", "paper_id", "user_id", "page_num", "section", "content_type", "content_data"],
        limit=5000,
    )
    if len(rows) < expected_count:
        raise RuntimeError(f"source rows not enough: got={len(rows)}, expected={expected_count}")
    return sorted(rows[:expected_count], key=lambda row: int(row.get("id") or 0))


def recreate_partial_target_collection(name: str, dim: int, alias: str) -> Collection:
    if utility.has_collection(name, using=alias):
        utility.drop_collection(name, using=alias)
    return ensure_target_collection(name, dim, alias)


def dump_dashboard(path: Path, dashboard: Dict[str, Any]) -> None:
    path.write_text(json.dumps(dashboard, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    args = parse_args()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    alias = "v23_build"
    connections.connect(alias=alias, host=args.milvus_host, port=args.milvus_port)

    dim = 0

    dashboard: Dict[str, Any] = {
        "provider": args.provider,
        "model": args.model,
        "dimension": dim,
        "stage_stats": {},
        "updated_at": time.time(),
    }

    report: Dict[str, Any] = {
        "provider": args.provider,
        "model": args.model,
        "dimension": dim,
        "dry_run": args.dry_run,
        "stages": {},
        "status": "PASS",
        "error": None,
    }

    try:
        provider = create_embedding_provider(args.provider, args.model)
        dim = provider.dimension()
        dashboard["dimension"] = dim
        report["dimension"] = dim

        for stage in stages_from_arg(args.stage):
            source_name = SOURCE_COLLECTIONS[stage]
            target_name = TARGET_COLLECTIONS_FLASH[stage]

            source = Collection(source_name, using=alias)
            rows = fetch_source_rows(source)
            target = ensure_target_collection(target_name, dim, alias)

            existing = target.num_entities if args.resume else 0
            if args.resume and existing >= 1451:
                report["stages"][stage] = {
                    "source_collection": source_name,
                    "target_collection": target_name,
                    "source_count": len(rows),
                    "target_count": existing,
                    "inserted": 0,
                    "status": "SKIPPED_RESUME",
                }
                continue
            if args.resume and 0 < existing < 1451:
                target = recreate_partial_target_collection(target_name, dim, alias)
                existing = 0

            inserted = 0
            i = 0
            next_dashboard_at = time.time() + args.dashboard_interval_seconds
            while i < len(rows):
                chunk = rows[i : i + args.batch_size]
                texts = [str(r.get("content_data") or "")[:30000] for r in chunk]
                vectors = provider.embed_texts(texts)
                if len(vectors) != len(chunk):
                    raise RuntimeError("provider returned mismatched vector count")

                if not args.dry_run:
                    payload = [
                        [str(r.get("id") or "") for r in chunk],
                        [r.get("paper_id", "") for r in chunk],
                        [r.get("user_id", "benchmark-user") for r in chunk],
                        [int(r.get("page_num") or 0) for r in chunk],
                        [str(r.get("section") or "")[:256] for r in chunk],
                        [str(r.get("content_type") or "text")[:64] for r in chunk],
                        [str(r.get("content_data") or "")[:65535] for r in chunk],
                        [stage for _ in chunk],
                        vectors,
                    ]
                    target.insert(payload)

                inserted += len(chunk)
                i += len(chunk)

                if time.time() >= next_dashboard_at:
                    dashboard["stage_stats"][stage] = {
                        "processed": inserted,
                        "total": len(rows),
                        "target_collection": target_name,
                    }
                    dashboard["updated_at"] = time.time()
                    dump_dashboard(out_dir / "api_flash_ingest_dashboard.json", dashboard)
                    next_dashboard_at = time.time() + args.dashboard_interval_seconds

            if not args.dry_run:
                target.flush()
            final_count = target.num_entities

            report["stages"][stage] = {
                "source_collection": source_name,
                "target_collection": target_name,
                "source_count": len(rows),
                "target_count": final_count,
                "inserted": inserted,
                "status": "OK",
            }

            dashboard["stage_stats"][stage] = {
                "processed": inserted,
                "total": len(rows),
                "target_collection": target_name,
                "target_count": final_count,
            }

        # strict count gate
        for stage in stages_from_arg(args.stage):
            stat = report["stages"].get(stage)
            if not stat:
                continue
            if stat["status"].startswith("SKIPPED"):
                if stat["target_count"] != 1451:
                    raise RuntimeError(f"resume target count invalid for {stage}: {stat['target_count']}")
            elif stat["target_count"] != 1451 and not args.dry_run:
                raise RuntimeError(f"target count invalid for {stage}: {stat['target_count']}")

    except Exception as e:
        report["status"] = "BLOCKED"
        report["error"] = str(e)

    dashboard["updated_at"] = time.time()
    dump_dashboard(out_dir / "api_flash_ingest_dashboard.json", dashboard)

    # markdown outputs
    (out_dir / "api_flash_ingest_dashboard.md").write_text(
        "# v2.3 API Flash Ingest Dashboard\n\n"
        + f"- provider: {args.provider}\n"
        + f"- model: {args.model}\n"
        + f"- dimension: {dim}\n\n"
        + "## Stage Stats\n\n"
        + "| stage | processed | total | target_count |\n"
        + "|---|---:|---:|---:|\n"
        + "\n".join(
            f"| {stage} | {dashboard['stage_stats'][stage].get('processed',0)} | {dashboard['stage_stats'][stage].get('total',0)} | {dashboard['stage_stats'][stage].get('target_count',0)} |"
            for stage in dashboard.get("stage_stats", {})
        )
        + "\n",
        encoding="utf-8",
    )

    (out_dir / "api_flash_ingest_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "api_flash_ingest_report.md").write_text(
        "# v2.3 API Flash Ingest Report\n\n"
        + f"- status: {report['status']}\n"
        + f"- provider: {args.provider}\n"
        + f"- model: {args.model}\n"
        + f"- dimension: {dim}\n"
        + f"- dry_run: {args.dry_run}\n",
        encoding="utf-8",
    )

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
