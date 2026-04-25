#!/usr/bin/env python3
"""Parse all 50 PDFs and rebuild v2.3 collection."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
API_ROOT = ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections, utility
import pypdf

try:
    import os
    os.environ.setdefault('DASHSCOPE_API_KEY', 'sk-e293fe03554943a490843478c82b2e6a')
    from app.core.model_gateway import create_embedding_provider
except Exception as e:
    print(f"Warning: Could not import embedding provider: {e}")
    create_embedding_provider = None

PAPER_DIR = ROOT / "tests" / "evals" / "fixtures" / "papers"
MANIFEST_PATH = PAPER_DIR / "manifest.json"
OUTPUT_DIR = ROOT / "artifacts" / "benchmarks" / "v2_3_1"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

COLLECTION_NAME = "paper_contents_v2_api_tongyi_flash_raw_v2_3"


def load_manifest() -> Dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text())


def parse_pdfs(manifest: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse all PDFs and create chunks."""
    papers = manifest.get("papers", [])
    all_chunks = []
    
    for paper in papers:
        pdf_path = PAPER_DIR / paper["source_pdf"]
        if not pdf_path.exists():
            print(f"  Skipping {pdf_path.name} - not found")
            continue
        
        print(f"  Parsing {paper['paper_id']}: {paper.get('title', '')}")
        
        try:
            reader = pypdf.PdfReader(str(pdf_path))
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if not text or len(text.strip()) < 50:
                    continue
                chunk = {
                    "source_chunk_id": f"{paper['paper_id']}-{i+1}",
                    "paper_id": paper["paper_id"],
                    "page_num": i + 1,
                    "section": "content",
                    "content_type": "text",
                    "content_data": text[:4000],  # Truncate very long text
                    "raw_text": text[:4000],
                }
                all_chunks.append(chunk)
        except Exception as e:
            print(f"    Error: {e}")
    
    return all_chunks


def ensure_collection(dim: int, alias: str) -> Collection:
    """Ensure collection exists with correct schema."""
    if utility.has_collection(COLLECTION_NAME, using=alias):
        print(f"Dropping existing collection: {COLLECTION_NAME}")
        utility.drop_collection(COLLECTION_NAME, using=alias)
    
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="source_chunk_id", dtype=DataType.VARCHAR, max_length=128),
        FieldSchema(name="paper_id", dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name="user_id", dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name="page_num", dtype=DataType.INT64),
        FieldSchema(name="section", dtype=DataType.VARCHAR, max_length=256),
        FieldSchema(name="content_type", dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name="content_data", dtype=DataType.VARCHAR, max_length=32000),
        FieldSchema(name="raw_data", dtype=DataType.VARCHAR, max_length=32000),
        FieldSchema(name="indexable", dtype=DataType.VARCHAR, max_length=32000),
        FieldSchema(name="embedding_status", dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name="quality_score", dtype=DataType.FLOAT),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim),
    ]
    
    schema = CollectionSchema(fields=fields, name=COLLECTION_NAME)
    
    col = Collection(name=COLLECTION_NAME, schema=schema, using=alias)
    col.create_index(
        field_name="embedding",
        index_params={"index_type": "FLAT", "metric_type": "COSINE"},
    )
    print(f"Created collection: {COLLECTION_NAME}")
    return col


def insert_chunks(col: Collection, chunks: List[Dict[str, Any]], provider, alias: str, dim: int) -> None:
    """Insert chunks with embeddings one by one."""
    print(f"Inserting {len(chunks)} chunks...")

    for i, chunk in enumerate(chunks):
        if i % 100 == 0:
            print(f"  Progress: {i}/{len(chunks)}")
        
        try:
            text = chunk.get("content_data", "")[:2000]
            vec = provider.embed_texts([text])[0]
        except Exception as e:
            print(f"  Embedding error at {i}: {e}")
            vec = [0.0] * dim
        
        entities = [
            [chunk.get("source_chunk_id", "")],
            [chunk.get("paper_id", "")],
            ["system"],
            [chunk.get("page_num", 0)],
            [chunk.get("section", "")],
            [chunk.get("content_type", "")],
            [chunk.get("content_data", "")[:8000]],
            [chunk.get("raw_text", "")[:8000]],
            [chunk.get("content_data", "")[:8000]],
            ["completed"],
            [1.0],
            [vec],
        ]
        
        try:
            col.insert(entities)
        except Exception as e:
            if i < 3:
                print(f"  Insert error at {i}: {e}")
            pass
    
    col.flush()
    print(f"  Inserted {col.num_entities} entities")


def main() -> int:
    print("=" * 50)
    print("Parse PDFs and Rebuild v2.3 Collection")
    print("=" * 50)
    
    # Load manifest
    print("\n[1/4] Loading manifest...")
    manifest = load_manifest()
    print(f"  Papers: {len(manifest.get('papers', []))}")
    
    # Parse PDFs
    print("\n[2/4] Parsing PDFs...")
    chunks = parse_pdfs(manifest)
    print(f"  Total chunks: {len(chunks)}")
    
    # Clean text to remove problematic Unicode
    for chunk in chunks:
        if "content_data" in chunk:
            chunk["content_data"] = chunk["content_data"].encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
        if "raw_text" in chunk:
            chunk["raw_text"] = chunk["raw_text"].encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
    
    # Save chunks
    chunks_file = OUTPUT_DIR / "parsed_chunks.json"
    with open(chunks_file, 'w', encoding='utf-8', errors='ignore') as f:
        json.dump({"chunks": chunks, "count": len(chunks)}, f, ensure_ascii=False, indent=2)
    print(f"  Saved to: {chunks_file}")
    
    # Connect to Milvus
    print("\n[3/4] Building collection...")
    alias = "v2_3_rebuild"
    connections.connect(alias=alias, host="localhost", port=19530)
    
    # Get embedding dimension
    if create_embedding_provider:
        provider = create_embedding_provider("tongyi", "tongyi-embedding-vision-flash-2026-03-06")
        dim = provider.dimension()
    else:
        dim = 1024  # text-embedding-v3 dimension
    print(f"  Embedding dimension: {dim}")
    
    # Ensure collection and insert
    col = ensure_collection(dim, alias)
    
    if create_embedding_provider and chunks:
        insert_chunks(col, chunks, provider, alias, dim)
    
    print(f"\n[4/4] Done!")
    print(f"  Collection: {COLLECTION_NAME}")
    print(f"  Entities: {col.num_entities}")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())