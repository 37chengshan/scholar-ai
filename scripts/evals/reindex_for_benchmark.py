"""
Re-index existing BGE-M3 chunks into Qwen v2.1 collections using Qwen embeddings.
Maps dataset-s-001 → per-paper v2-p-XXX IDs based on source_pdf paths.
"""
import sys
sys.path.insert(0, "apps/api")
import os
os.environ["EMBEDDING_MODEL"] = "qwen3-vl-2b"

import json
import asyncio
import warnings
warnings.filterwarnings("ignore")

print("Step 1: Load BGE-M3 collection chunks...", flush=True)
from app.core.milvus_service import get_milvus_service
from pymilvus import Collection

svc = get_milvus_service()
svc.connect()

bge_col = Collection("paper_contents_v2", using=svc._alias)
bge_col.load()
rows = bge_col.query(
    expr="indexable == true",
    output_fields=[
        "paper_id", "user_id", "page_num", "content_type", "section",
        "quality_score", "word_count", "has_equations", "has_figures",
        "extraction_version", "content_data", "raw_data", "indexable", "embedding_status",
    ],
    limit=500,
)
print(f"  Got {len(rows)} chunks", flush=True)

# Map source_pdf arXiv IDs -> v2-p-XXX (expand as needed)
ARXIV_TO_VPID = {
    "2303.08774": "v2-p-001",
    "2304.07193": "v2-p-002",
    "2304.12244": "v2-p-003",
    "2305.11206": "v2-p-004",
    "2306.05685": "v2-p-005",
    "2307.09288": "v2-p-006",
    "2310.03744": "v2-p-007",
    "2310.08923": "v2-p-008",
    "2311.12345": "v2-p-009",
    "2311.16634": "v2-p-010",
    "2311.16982": "v2-p-011",
    "2311.17166": "v2-p-012",
    "2311.17589": "v2-p-013",
    "2311.18822": "v2-p-014",
    "2312.02200": "v2-p-015",
    "2312.02600": "v2-p-016",
    "2312.02806": "v2-p-017",
    "2312.03090": "v2-p-018",
    "2312.04822": "v2-p-019",
    "2312.05487": "v2-p-020",
}


def arxiv_from_raw(raw_data):
    if isinstance(raw_data, dict):
        src = raw_data.get("source_pdf", "")
    elif isinstance(raw_data, str):
        try:
            d = json.loads(raw_data)
            src = d.get("source_pdf", "")
        except Exception:
            src = raw_data
    else:
        src = ""
    for arxiv_id, vpid in ARXIV_TO_VPID.items():
        if arxiv_id in str(src):
            return vpid
    return None


# Remap chunks to v2-p-XXX IDs
remapped = []
skipped = 0
for r in rows:
    vpid = arxiv_from_raw(r.get("raw_data", {}))
    if vpid is None:
        skipped += 1
        continue
    remapped.append({**r, "paper_id": vpid})

print(f"  Remapped {len(remapped)} chunks, skipped {skipped}", flush=True)
if not remapped:
    print("ERROR: No chunks remapped. Check raw_data source_pdf fields.", flush=True)
    sys.exit(1)

print("Step 2: Load Qwen3-VL model...", flush=True)
from app.core.qwen3vl_service import Qwen3VLMultimodalEmbedding

qwen_svc = Qwen3VLMultimodalEmbedding()
qwen_svc.load_model()
print(f"  Model loaded, dim={qwen_svc.get_embedding_dim()}", flush=True)


print("Step 3: Generate Qwen embeddings...", flush=True)
texts = [r["content_data"] for r in remapped]
embeddings = []
batch_size = 4
for i in range(0, len(texts), batch_size):
    batch = texts[i : i + batch_size]
    for t in batch:
        vec = qwen_svc.encode_text(t)
        embeddings.append(vec)
    print(f"  Embedded {min(i + batch_size, len(texts))}/{len(texts)}", flush=True)
print(f"  Got {len(embeddings)} embeddings, dim={len(embeddings[0]) if embeddings else 0}", flush=True)

print("Step 4: Insert into Qwen collections...", flush=True)
target_collections = [
    "paper_contents_v2_qwen_v2_raw_v2_1",
    "paper_contents_v2_qwen_v2_rule_v2_1",
    "paper_contents_v2_qwen_v2_llm_v2_1",
]

for col_name in target_collections:
    col = Collection(col_name, using=svc._alias)
    col.load()

    insert_data = [
        [r["paper_id"] for r in remapped],                     # paper_id
        ["benchmark-user"] * len(remapped),                    # user_id
        [int(r.get("page_num", 0) or 0) for r in remapped],   # page_num
        [r.get("content_type", "text") or "text" for r in remapped],  # content_type
        [r.get("section", "") or "" for r in remapped],        # section
        [float(r.get("quality_score", 1.0) or 1.0) for r in remapped],  # quality_score
        [int(r.get("word_count", 0) or 0) for r in remapped], # word_count
        [bool(r.get("has_equations", False)) for r in remapped],  # has_equations
        [bool(r.get("has_figures", False)) for r in remapped],   # has_figures
        [int(r.get("extraction_version", 2) or 2) for r in remapped],  # extraction_version
        [r.get("content_data", "") or "" for r in remapped],   # content_data
        [
            json.dumps(r.get("raw_data", {})) if isinstance(r.get("raw_data"), dict)
            else (r.get("raw_data") or "{}")
            for r in remapped
        ],  # raw_data
        embeddings,                                            # embedding
        [True] * len(remapped),                               # indexable
        ["success"] * len(remapped),                          # embedding_status
    ]

    col.insert(insert_data)
    col.flush()

    # Ensure vector index exists
    existing_indexes = [idx.field_name for idx in col.indexes]
    if "embedding" not in existing_indexes:
        col.create_index(
            "embedding",
            {"index_type": "FLAT", "metric_type": "IP", "params": {}},
        )
    col.load()
    print(f"  Inserted {len(remapped)} into {col_name}, total={col.num_entities}", flush=True)

print("Done! Re-indexing complete.", flush=True)
