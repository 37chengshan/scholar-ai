#!/usr/bin/env python3
"""Rebuild v2.3 collection with correct paper IDs using existing parsed data + new manifest."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
API_ROOT = ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections, utility

PAPER_DIR = ROOT / "tests" / "evals" / "fixtures" / "papers"
MANIFEST_PATH = PAPER_DIR / "manifest.json"
CHUNKS_PATH = ROOT / "artifacts" / "benchmarks" / "v2.1" / "raw_base" / "raw_chunks.jsonl"

OUTPUT_COLLECTIONS = {
    "raw": "paper_contents_v2_api_tongyi_flash_raw_v2_3",
    "rule": "paper_contents_v2_api_tongyi_flash_rule_v2_3", 
    "llm": "paper_contents_v2_api_tongyi_flash_llm_v2_3",
}


def load_manifest() -> Dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text())


def load_chunks() -> List[Dict[str, Any]]:
    chunks = []
    for line in CHUNKS_PATH.read_text().splitlines():
        if line.strip():
            chunks.append(json.loads(line))
    return chunks


def build_paper_id_map(manifest: Dict[str, Any]) -> Dict[str, str]:
    """Map: old_paper_id -> new_paper_id"""
    old_to_new = {}
    for i, entry in enumerate(manifest.get("papers", [])):
        old_id = f"v2-p-{i+1:03d}"  # v2-p-001, v2-p-002, etc
        new_id = entry.get("paper_id", old_id)
        old_to_new[old_id] = new_id
    return old_to_new


def ensure_collection(name: str, dim: int, alias: str) -> Collection:
    if utility.has_collection(name, using=alias):
        utility.drop_collection(name, using=alias)
    
    schema = CollectionSchema(
        fields=[
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="source_chunk_id", dtype=DataType.VARCHAR, max_length=128),
            FieldSchema(name="paper_id", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="user_id", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="page_num", dtype=DataType.INT64),
            FieldSchema(name="section", dtype=DataType.VARCHAR, max_length=256),
            FieldSchema(name="content_type", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="content_data", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="raw_data", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="indexable", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="embedding_status", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="quality_score", dtype=DataType.FLOAT),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim),
        ],
        name=name,
    )
    col = Collection(name=name, schema=schema, using=alias)
    col.create_index(
        field_name="embedding",
        index_params={"index_type": "FLAT", "metric_type": "COSINE"},
    )
    return col


def main() -> int:
    print("Loading manifest and chunks...")
    manifest = load_manifest()
    chunks = load_chunks()
    paper_id_map = build_paper_id_map(manifest)
    
    print(f"Manifest papers: {len(manifest.get('papers', []))}")
    print(f"Original chunks: {len(chunks)}")
    print(f"Paper ID map: {paper_id_map}")
    
    # Update chunks with new paper_ids
    updated_chunks = []
    for chunk in chunks:
        old_pid = chunk.get("paper_id", "v2-p-001")
        new_pid = paper_id_map.get(old_pid, old_pid)
        chunk["paper_id"] = new_pid
        updated_chunks.append(chunk)
    
    # Also add more chunks if we have more papers in manifest
    extra_papers = len(manifest.get("papers", [])) - len(chunks)
    print(f"Extra papers to add: {extra_papers}")
    
    # Deduplicate by paper_id (take first page as representative)
    by_paper = {}
    for chunk in updated_chunks:
        pid = chunk.get("paper_id", "")
        if pid not in by_paper:
            by_paper[pid] = chunk
    
    print(f"Unique papers after mapping: {len(by_paper)}")
    
    # Show first few mappings
    for i, (pid, chunk) in enumerate(list(by_paper.items())[:5]):
        print(f"  {pid}: {chunk.get('raw_text', '')[:80]}...")
    
    print("\nNeed to re-parse 50 new PDFs with correct paper IDs.")
    print("This requires running docling/pypdf parser.")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())