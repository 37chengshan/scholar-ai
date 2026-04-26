#!/usr/bin/env python
"""Build stage variant from cached raw chunks (raw/rule/llm)."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
from pathlib import Path
from typing import Any, Optional

from zhipuai import ZhipuAI

ROOT = Path(__file__).resolve().parent.parent
API_ROOT = ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.config import settings
from app.core.contextual_chunk_builder import enrich_chunk
from app.core.embedding.factory import get_embedding_service
from app.core.milvus_service import get_milvus_service
from app.core.qdrant_service import get_qdrant_service

DATASET_PROFILE_TO_COUNT = {
    "large-baseline": 12,
    "v2": 20,
    "v2.1": 20,
    "xlarge-main": 50,
}

_HIGH_VALUE_PATTERN = re.compile(
    r"\b(table|figure|fig\.?|ablation|benchmark|accuracy|recall|precision|f1|ndcg|mrr|compare|\d+\.\d+|\d+%)\b",
    re.IGNORECASE,
)


def _is_high_value_chunk(chunk_text: str) -> bool:
    txt = chunk_text or ""
    if len(txt) < 180:
        return True
    return bool(_HIGH_VALUE_PATTERN.search(txt))


def _llm_contextual_prefix(
    client: Optional[ZhipuAI],
    raw_text: str,
    paper_title: str,
    section: str,
    page_num: int,
    max_chars: int,
) -> Optional[str]:
    if client is None:
        return None

    prompt = (
        "You are enriching an academic retrieval chunk. "
        "Generate a short factual context prefix in English. "
        "Do not invent facts, do not rewrite raw text, no bullets, no markdown. "
        f"Limit to {max_chars} characters.\n\n"
        f"Paper: {paper_title}\n"
        f"Section: {section}\n"
        f"Page: {page_num}\n"
        f"Raw chunk:\n{raw_text[:1400]}"
    )
    response = client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[
            {"role": "system", "content": "Return only short contextual prefix text."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=180,
    )
    content = ((response.choices or [])[0].message.content or "").strip()
    return content[:max_chars] if content else None


def load_raw_chunks(raw_chunks_jsonl: Path) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    with raw_chunks_jsonl.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                chunks.append(json.loads(line))
    return chunks


def apply_stage_transformation(
    raw_chunk: dict[str, Any],
    stage: str,
    llm_client: Optional[ZhipuAI],
    llm_max_chars: int,
) -> dict[str, Any]:
    raw_text = str(raw_chunk.get("raw_chunk_text") or "")
    section = str(raw_chunk.get("section_path") or raw_chunk.get("subsection") or "Body")
    page_num = int(raw_chunk.get("page_num") or 1)

    contextual_prefix = ""
    content_data = raw_text

    if stage in {"rule", "llm"}:
        enriched = enrich_chunk(
            chunk={
                "text": raw_text,
                "page_num": page_num,
                "section": section,
                "subsection": str(raw_chunk.get("subsection") or section),
            },
            paper_title=str(raw_chunk.get("metadata", {}).get("title") or "unknown"),
            all_page_items=[{"text": raw_text, "page_num": page_num, "section": section}],
            chunk_index=max(int(raw_chunk.get("metadata", {}).get("chunk_index", 1)) - 1, 0),
            window_size=1,
        )
        contextual_prefix = str(enriched.get("contextual_prefix") or "")
        content_data = str(enriched.get("content_data") or raw_text)

    if stage == "llm" and _is_high_value_chunk(raw_text):
        try:
            llm_prefix = _llm_contextual_prefix(
                client=llm_client,
                raw_text=raw_text,
                paper_title=str(raw_chunk.get("metadata", {}).get("title") or "unknown"),
                section=section,
                page_num=page_num,
                max_chars=llm_max_chars,
            )
            if llm_prefix:
                contextual_prefix = llm_prefix
                content_data = f"{llm_prefix}\n{raw_text}"
        except Exception:
            pass

    source_chunk_id = str(raw_chunk.get("source_chunk_id") or raw_chunk.get("raw_chunk_id") or "")
    return {
        "paper_id": raw_chunk["paper_id"],
        "user_id": "benchmark-user",
        "content_type": "text",
        "page_num": page_num,
        "section": section,
        "text": raw_text,
        "raw_text": raw_text,
        "contextual_prefix": contextual_prefix,
        "content_data": content_data,
        "stage": stage,
        "source_chunk_id": source_chunk_id,
        "raw_data": {
            "stage": stage,
            "source_chunk_id": source_chunk_id,
            "source_pdf": raw_chunk.get("source_pdf"),
            "raw_chunk_id": raw_chunk.get("raw_chunk_id"),
            "metadata": raw_chunk.get("metadata", {}),
        },
    }


def delete_stage_records(user_id: str) -> None:
    if settings.VECTOR_STORE_BACKEND == "qdrant":
        qdrant = get_qdrant_service()
        qdrant.ensure_collection(vector_size=settings.EMBEDDING_DIMENSION)
        return

    milvus = get_milvus_service()
    collection = milvus.get_collection(settings.MILVUS_COLLECTION_CONTENTS_V2)
    collection.delete(f'user_id == "{user_id}"')
    collection.flush()


def load_existing_source_chunk_ids(user_id: str, stage: str) -> set[str]:
    if settings.VECTOR_STORE_BACKEND == "qdrant":
        return set()

    milvus = get_milvus_service()
    collection = milvus.get_collection(settings.MILVUS_COLLECTION_CONTENTS_V2)

    source_chunk_ids: set[str] = set()
    last_id = 0
    page_size = 1000

    while True:
        expr = f'user_id == "{user_id}" and id > {last_id}'
        rows = collection.query(
            expr=expr,
            output_fields=["id", "raw_data"],
            limit=page_size,
        )
        if not rows:
            break

        for row in rows:
            row_id = int(row.get("id") or 0)
            if row_id > last_id:
                last_id = row_id

            raw_data = row.get("raw_data") or {}
            if not isinstance(raw_data, dict):
                continue
            if str(raw_data.get("stage") or "") != stage:
                continue

            source_chunk_id = str(raw_data.get("source_chunk_id") or "").strip()
            if source_chunk_id:
                source_chunk_ids.add(source_chunk_id)

        if len(rows) < page_size:
            break

    return source_chunk_ids


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build stage variants from raw base")
    parser.add_argument("--dataset-profile", choices=list(DATASET_PROFILE_TO_COUNT.keys()), default="v2")
    parser.add_argument("--stage", choices=["raw", "rule", "llm"], required=True)
    parser.add_argument("--user-id", default="benchmark-user")
    parser.add_argument("--embedding-batch-size", type=int, default=12)
    parser.add_argument("--llm-prefix-max-chars", type=int, default=360)
    parser.add_argument("--output-dir", default=str(ROOT / "artifacts" / "benchmarks"))
    parser.add_argument("--skip-if-complete", action="store_true")
    parser.add_argument("--rebuild", action="store_true")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    raw_base_dir = out_dir / args.dataset_profile / "raw_base"
    raw_chunks_jsonl = raw_base_dir / "raw_chunks.jsonl"
    if not raw_chunks_jsonl.exists():
        print(f"[build-variant] error raw_chunks missing: {raw_chunks_jsonl}")
        return 1

    variant_dir = out_dir / args.dataset_profile / "variants"
    variant_dir.mkdir(parents=True, exist_ok=True)
    timing_jsonl = variant_dir / f"timing_{args.stage}.jsonl"
    summary_json = variant_dir / f"summary_{args.stage}.json"

    if args.skip_if_complete and summary_json.exists():
        print(f"[build-variant] skip completed stage={args.stage} summary={summary_json}")
        return 0

    start_total = time.time()
    raw_chunks = load_raw_chunks(raw_chunks_jsonl)
    print(f"[build-variant] stage={args.stage} raw_chunks={len(raw_chunks)}")

    llm_client: Optional[ZhipuAI] = None
    if args.stage == "llm" and settings.ZHIPU_API_KEY:
        llm_client = ZhipuAI(api_key=settings.ZHIPU_API_KEY)

    embedding_service = get_embedding_service()
    embedding_service.load_model()

    if settings.VECTOR_STORE_BACKEND == "qdrant":
        qdrant = get_qdrant_service()
        qdrant.ensure_collection(vector_size=settings.EMBEDDING_DIMENSION)
    else:
        milvus = get_milvus_service()
        milvus.connect()
        milvus.get_collection(settings.MILVUS_COLLECTION_CONTENTS_V2)

    existing_source_chunk_ids: set[str] = set()
    if args.rebuild:
        delete_stage_records(args.user_id)
        print(f"[build-variant] rebuild stage={args.stage} cleared existing records for user={args.user_id}")
    else:
        existing_source_chunk_ids = load_existing_source_chunk_ids(args.user_id, args.stage)
        print(
            f"[build-variant] resume stage={args.stage} existing_chunks={len(existing_source_chunk_ids)}"
        )

    grouped: dict[str, list[dict[str, Any]]] = {}
    for chunk in raw_chunks:
        source_chunk_id = str(
            chunk.get("source_chunk_id") or chunk.get("raw_chunk_id") or ""
        ).strip()
        if source_chunk_id and source_chunk_id in existing_source_chunk_ids:
            continue
        grouped.setdefault(chunk["paper_id"], []).append(chunk)

    pending_chunk_count = sum(len(chunks) for chunks in grouped.values())
    if pending_chunk_count == 0:
        summary = {
            "dataset_profile": args.dataset_profile,
            "stage": args.stage,
            "paper_count": 0,
            "chunk_count": len(raw_chunks),
            "pending_chunk_count": 0,
            "existing_chunk_count": len(existing_source_chunk_ids),
            "inserted_count": 0,
            "build_rule_seconds": 0.0,
            "build_llm_seconds": 0.0,
            "embed_dense_seconds": 0.0,
            "build_sparse_seconds": 0.0,
            "insert_index_seconds": 0.0,
            "summary_index_seconds": round(time.time() - start_total, 4),
            "timing_jsonl": str(timing_jsonl),
            "resume_mode": not args.rebuild,
        }
        _write_jsonl(timing_jsonl, [])
        summary_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[build-variant] stage={args.stage} already complete")
        print(f"[build-variant] summary={summary_json}")
        return 0

    print(
        f"[build-variant] stage={args.stage} pending_papers={len(grouped)} pending_chunks={pending_chunk_count}"
    )

    timing_rows: list[dict[str, Any]] = []
    insert_total = 0
    embed_total = 0.0
    insert_total_sec = 0.0

    for p_idx, (paper_id, chunks) in enumerate(grouped.items(), start=1):
        paper_start = time.time()

        transform_start = time.time()
        stage_chunks = [
            apply_stage_transformation(
                raw_chunk=chunk,
                stage=args.stage,
                llm_client=llm_client,
                llm_max_chars=args.llm_prefix_max_chars,
            )
            for chunk in chunks
        ]
        transform_sec = time.time() - transform_start

        total_batches = math.ceil(len(stage_chunks) / args.embedding_batch_size) if stage_chunks else 0
        paper_inserted = 0
        paper_embed_sec = 0.0
        paper_insert_sec = 0.0

        for batch_idx, batch_start in enumerate(range(0, len(stage_chunks), args.embedding_batch_size), start=1):
            batch_chunks = stage_chunks[batch_start : batch_start + args.embedding_batch_size]
            batch_texts = [item["content_data"] for item in batch_chunks]

            embed_start = time.time()
            batch_embeddings = embedding_service.encode_text(batch_texts)
            batch_embed_sec = time.time() - embed_start
            paper_embed_sec += batch_embed_sec

            encoded_chunks = [{**item, "embedding": emb} for item, emb in zip(batch_chunks, batch_embeddings)]

            insert_start = time.time()
            if settings.VECTOR_STORE_BACKEND == "qdrant":
                ids = qdrant.upsert_contents_batched(encoded_chunks)
            else:
                ids = milvus.insert_contents_batched(encoded_chunks)
            batch_insert_sec = time.time() - insert_start
            paper_insert_sec += batch_insert_sec

            paper_inserted += len(ids)
            insert_total += len(ids)
            print(
                f"[build-variant] ({p_idx}/{len(grouped)}) {paper_id} "
                f"batch {batch_idx}/{total_batches} inserted={paper_inserted}"
            )

        build_rule = transform_sec if args.stage == "rule" else 0.0
        build_llm = transform_sec if args.stage == "llm" else 0.0
        paper_total = time.time() - paper_start

        timing_rows.append(
            {
                "paper_id": paper_id,
                "parse_pdf_seconds": 0.0,
                "chunk_raw_seconds": 0.0,
                "build_rule_seconds": round(build_rule, 4),
                "build_llm_seconds": round(build_llm, 4),
                "embed_dense_seconds": round(paper_embed_sec, 4),
                "build_sparse_seconds": 0.0,
                "insert_index_seconds": round(paper_insert_sec, 4),
                "summary_index_seconds": round(paper_total, 4),
                "stage": args.stage,
                "chunk_count": len(chunks),
                "inserted_count": paper_inserted,
            }
        )

        embed_total += paper_embed_sec
        insert_total_sec += paper_insert_sec

    _write_jsonl(timing_jsonl, timing_rows)

    summary = {
        "dataset_profile": args.dataset_profile,
        "stage": args.stage,
        "paper_count": len(grouped),
        "chunk_count": len(raw_chunks),
        "pending_chunk_count": pending_chunk_count,
        "existing_chunk_count": len(existing_source_chunk_ids),
        "inserted_count": insert_total,
        "build_rule_seconds": round(sum(r["build_rule_seconds"] for r in timing_rows), 4),
        "build_llm_seconds": round(sum(r["build_llm_seconds"] for r in timing_rows), 4),
        "embed_dense_seconds": round(embed_total, 4),
        "build_sparse_seconds": 0.0,
        "insert_index_seconds": round(insert_total_sec, 4),
        "summary_index_seconds": round(time.time() - start_total, 4),
        "timing_jsonl": str(timing_jsonl),
        "resume_mode": not args.rebuild,
    }
    summary_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"[build-variant] stage={args.stage} done inserted={insert_total}")
    print(f"[build-variant] summary={summary_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
