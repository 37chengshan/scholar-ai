#!/usr/bin/env python3
"""SPECTER2 Isolated Embedding Worker.

This script MUST be run inside .venv-specter2 (transformers==4.39.x + adapters==0.2.1).
It is intentionally isolated from the main API venv which requires transformers>=4.57.0.

Modes:
  --mode probe          Verify environment and write specter2_env_probe.json/.md
  --mode anchor-eval    Run SPECTER2 anchor Hit@5 eval against Milvus
  --mode all            Run probe then anchor-eval

Usage (always call with .venv-specter2 python):
  .venv-specter2/bin/python scripts/evals/specter2_embed_worker.py \\
      --mode all \\
      --milvus-host localhost --milvus-port 19530 \\
      --output-dir artifacts/benchmarks/v2_2_1
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ──────────────────────────────────────────────────────────
# Guard: refuse to run in the main API venv (transformers>=4.57)
# ──────────────────────────────────────────────────────────
try:
    import transformers as _tf

    _tf_ver = tuple(int(x) for x in _tf.__version__.split(".")[:2])
    if _tf_ver >= (4, 50):
        print(
            f"ERROR: transformers {_tf.__version__} detected. "
            "This script must be run inside .venv-specter2 (transformers~=4.39). "
            "Use: .venv-specter2/bin/python scripts/evals/specter2_embed_worker.py",
            file=sys.stderr,
        )
        sys.exit(2)
except ImportError:
    pass  # will fail later with a clearer message

# ──────────────────────────────────────────────────────────
# Benchmark query definitions (SPECTER2 families: compare/survey/evolution)
# ──────────────────────────────────────────────────────────
SPECTER2_QUERIES = [
    # cross-paper compare queries – expect multi-paper results
    {
        "query_id": "sp2-cmp-001",
        "family": "compare",
        "query": "Compare the attention mechanisms used in transformer-based models for NLP and vision.",
        "expected_papers": ["v2-p-001", "v2-p-002", "v2-p-003"],
    },
    {
        "query_id": "sp2-cmp-002",
        "family": "compare",
        "query": "How do different large language models handle long-context understanding?",
        "expected_papers": ["v2-p-004", "v2-p-005", "v2-p-006"],
    },
    {
        "query_id": "sp2-cmp-003",
        "family": "compare",
        "query": "What are the differences in training strategies between GPT-style and BERT-style models?",
        "expected_papers": ["v2-p-007", "v2-p-008"],
    },
    # survey queries – expect broad coverage across papers
    {
        "query_id": "sp2-sur-001",
        "family": "survey",
        "query": "Survey of vision-language models and multimodal representation learning.",
        "expected_papers": ["v2-p-009", "v2-p-010", "v2-p-011"],
    },
    {
        "query_id": "sp2-sur-002",
        "family": "survey",
        "query": "Overview of parameter-efficient fine-tuning methods for large models.",
        "expected_papers": ["v2-p-012", "v2-p-013"],
    },
    # evolution / related-work queries
    {
        "query_id": "sp2-evo-001",
        "family": "evolution",
        "query": "How has the field of in-context learning evolved since GPT-3?",
        "expected_papers": ["v2-p-014", "v2-p-015", "v2-p-016"],
    },
    {
        "query_id": "sp2-evo-002",
        "family": "evolution",
        "query": "Evolution of retrieval-augmented generation systems and their benchmarks.",
        "expected_papers": ["v2-p-017", "v2-p-018", "v2-p-019", "v2-p-020"],
    },
]

# anchor collection has 20 papers (v2-p-001..v2-p-020)
ALL_PAPER_IDS = {f"v2-p-{i:03d}" for i in range(1, 21)}


# ──────────────────────────────────────────────────────────
# Probe
# ──────────────────────────────────────────────────────────

def run_probe(output_dir: Path) -> Dict[str, Any]:
    """Verify SPECTER2 environment and return probe result dict."""
    result: Dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "main_transformers_version": "n/a (run in specter2 venv)",
        "specter2_transformers_version": "unknown",
        "adapters_version": "unknown",
        "specter2_model_name": "allenai/specter2_base",
        "adapter_name": "adhoc_query",
        "embedding_dim": 0,
        "adapter_loaded": False,
        "status": "BLOCKED",
        "error": None,
    }

    try:
        import transformers as _tf
        result["specter2_transformers_version"] = _tf.__version__
    except ImportError as e:
        result["error"] = f"transformers import failed: {e}"
        _write_probe(output_dir, result)
        return result

    try:
        import adapters as _ad
        result["adapters_version"] = _ad.__version__
    except ImportError as e:
        result["error"] = f"adapters import failed: {e}"
        _write_probe(output_dir, result)
        return result

    # Try actually loading model
    try:
        from adapters import AutoAdapterModel
        from transformers import AutoTokenizer

        base_model = "allenai/specter2_base"
        adapter_name = "adhoc_query"
        adapter_hf_path = "allenai/specter2_adhoc_query"

        print(f"[probe] Loading tokenizer from {base_model} ...")
        tokenizer = AutoTokenizer.from_pretrained(base_model)

        print(f"[probe] Loading base model from {base_model} ...")
        model = AutoAdapterModel.from_pretrained(base_model)

        print(f"[probe] Loading adapter {adapter_hf_path} ...")
        loaded_name = model.load_adapter(adapter_hf_path, source="hf")
        model.set_active_adapters(loaded_name)

        # Probe embedding dimension
        import torch

        model.eval()
        inputs = tokenizer("test sentence for dimension probing", return_tensors="pt", truncation=True)
        with torch.no_grad():
            out = model(**inputs)
        cls_vec = out.last_hidden_state[:, 0, :].squeeze(0)
        dim = int(cls_vec.shape[0])

        result["embedding_dim"] = dim
        result["adapter_loaded"] = True
        result["status"] = "PASS"
        print(f"[probe] ✅ PASS — dim={dim}, adapter=adhoc_query")

    except Exception as e:
        result["error"] = str(e)
        result["status"] = "BLOCKED"
        print(f"[probe] ❌ BLOCKED — {e}", file=sys.stderr)

    _write_probe(output_dir, result)
    return result


def _write_probe(output_dir: Path, result: Dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "specter2_env_probe.json"
    md_path = output_dir / "specter2_env_probe.md"

    with open(json_path, "w") as f:
        json.dump(result, f, indent=2)

    status_icon = "✅" if result["status"] == "PASS" else "❌"
    md = f"""# SPECTER2 Environment Probe

- status: {status_icon} **{result["status"]}**
- ts: {result["ts"]}

## Versions

| key | value |
|---|---|
| specter2_transformers_version | `{result["specter2_transformers_version"]}` |
| adapters_version | `{result["adapters_version"]}` |
| specter2_model_name | `{result["specter2_model_name"]}` |
| adapter_name | `{result["adapter_name"]}` |
| embedding_dim | {result["embedding_dim"]} |
| adapter_loaded | {result["adapter_loaded"]} |

"""
    if result.get("error"):
        md += f"## Error\n\n```\n{result['error']}\n```\n"

    with open(md_path, "w") as f:
        f.write(md)

    print(f"[probe] Written: {json_path}")
    print(f"[probe] Written: {md_path}")


# ──────────────────────────────────────────────────────────
# Anchor Eval
# ──────────────────────────────────────────────────────────

def run_anchor_eval(
    output_dir: Path,
    milvus_host: str,
    milvus_port: int,
    top_k: int = 5,
    probe_result: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run SPECTER2 anchor Hit@5 eval.

    Returns dict with anchor_hit_at_5, cross_paper_hit_at_5, avg_latency_s, etc.
    """
    result: Dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "status": "BLOCKED",
        "collection": "paper_contents_v2_specter2_sci_anchor_v2_1",
        "query_count": 0,
        "anchor_hit_at_5": 0.0,
        "cross_paper_hit_at_5": 0.0,
        "avg_latency_s": 0.0,
        "fallback_used": False,
        "error": None,
        "details": [],
        "gate": {
            "anchor_pass": False,
            "cross_pass": False,
            "latency_pass": False,
            "overall": "BLOCKED",
        },
    }

    # ── load model ──────────────────────────────────────
    try:
        from adapters import AutoAdapterModel
        from transformers import AutoTokenizer
        import torch

        base_model = "allenai/specter2_base"
        adapter_hf = "allenai/specter2_adhoc_query"

        print("[anchor-eval] Loading SPECTER2 model + adhoc_query adapter ...")
        tokenizer = AutoTokenizer.from_pretrained(base_model)
        model = AutoAdapterModel.from_pretrained(base_model)
        loaded_name = model.load_adapter(adapter_hf, source="hf")
        model.set_active_adapters(loaded_name)
        model.eval()
        print("[anchor-eval] Model loaded.")
    except Exception as e:
        result["error"] = f"model load failed: {e}"
        result["status"] = "BLOCKED"
        _write_anchor_eval(output_dir, result)
        return result

    # ── probe embedding dim ──────────────────────────────
    try:
        inputs = tokenizer("probe", return_tensors="pt", truncation=True)
        with torch.no_grad():
            out = model(**inputs)
        cls_probe = out.last_hidden_state[:, 0, :].squeeze(0)
        embed_dim = int(cls_probe.shape[0])
        print(f"[anchor-eval] Embedding dim probed: {embed_dim}")
    except Exception as e:
        result["error"] = f"dim probe failed: {e}"
        _write_anchor_eval(output_dir, result)
        return result

    # ── connect Milvus ───────────────────────────────────
    try:
        from pymilvus import connections, Collection, utility

        alias = "sp2_eval"
        connections.connect(alias=alias, host=milvus_host, port=milvus_port)
        print(f"[anchor-eval] Connected to Milvus {milvus_host}:{milvus_port}")
    except Exception as e:
        result["error"] = f"Milvus connect failed: {e}"
        _write_anchor_eval(output_dir, result)
        return result

    # ── select collection ────────────────────────────────
    anchor_collection = "paper_contents_v2_specter2_sci_anchor_v2_1"
    if not utility.has_collection(anchor_collection, using=alias):
        anchor_collection = "paper_contents_v2_specter2_raw_v2_1"
    if not utility.has_collection(anchor_collection, using=alias):
        result["error"] = "no SPECTER2 collections found in Milvus"
        result["status"] = "BLOCKED"
        _write_anchor_eval(output_dir, result)
        return result

    result["collection"] = anchor_collection
    col = Collection(anchor_collection, using=alias)
    col.load()
    entity_count = col.num_entities
    print(f"[anchor-eval] Collection {anchor_collection}: {entity_count} entities")

    # Verify dim matches
    for field in col.schema.fields:
        if field.name == "embedding":
            col_dim = field.params.get("dim", 0)
            if col_dim != embed_dim:
                result["error"] = f"dim mismatch: model={embed_dim}, collection={col_dim}"
                result["status"] = "BLOCKED"
                _write_anchor_eval(output_dir, result)
                return result
            print(f"[anchor-eval] Dim match: {embed_dim} ✓")

    # ── run queries ──────────────────────────────────────
    def embed_query(text: str) -> List[float]:
        inputs = tokenizer(
            text, return_tensors="pt", truncation=True, max_length=512
        )
        with torch.no_grad():
            out = model(**inputs)
        vec = out.last_hidden_state[:, 0, :].squeeze(0).tolist()
        return vec

    anchor_hits = 0
    anchor_total = 0
    cross_hits = 0
    cross_total = 0
    latencies = []
    details = []

    for row in SPECTER2_QUERIES:
        expected = set(row["expected_papers"])
        # filter to papers actually in the collection
        valid_expected = expected & ALL_PAPER_IDS

        t0 = time.perf_counter()
        vec = embed_query(row["query"])
        res = col.search(
            data=[vec],
            anns_field="embedding",
            param={"metric_type": "COSINE", "params": {"nprobe": 10}},
            limit=top_k,
            output_fields=["paper_id", "section"],
            using=alias,
        )
        latency = time.perf_counter() - t0
        latencies.append(latency)

        hit_papers = set()
        for hits in res:
            for h in hits:
                # pymilvus 2.4.x: access via h.fields or h.entity dict
                try:
                    if hasattr(h, "fields") and h.fields:
                        pid = h.fields.get("paper_id", "")
                    elif hasattr(h.entity, "get"):
                        pid = h.entity.get("paper_id", "")
                    else:
                        pid = h.entity["paper_id"] if "paper_id" in h.entity else ""
                except (TypeError, KeyError):
                    pid = ""
                if pid:
                    hit_papers.add(pid)

        # anchor hit: any expected paper found in top-k?
        anchor_hit = bool(hit_papers & valid_expected) if valid_expected else False
        anchor_total += 1
        if anchor_hit:
            anchor_hits += 1

        # cross-paper hit: at least 2 different papers in top-k results?
        cross_hit = len(hit_papers) >= 2
        cross_total += 1
        if cross_hit:
            cross_hits += 1

        detail = {
            "query_id": row["query_id"],
            "family": row["family"],
            "query": row["query"][:80],
            "expected_papers": sorted(valid_expected),
            "hit_papers": sorted(hit_papers),
            "anchor_hit": anchor_hit,
            "cross_paper_hit": cross_hit,
            "latency_s": round(latency, 4),
        }
        details.append(detail)
        icon = "✓" if anchor_hit else "✗"
        print(
            f"  [{icon}] {row['query_id']} anchor={anchor_hit} "
            f"cross={cross_hit} lat={latency:.3f}s "
            f"hits={sorted(hit_papers)}"
        )

    # ── compute metrics ──────────────────────────────────
    anchor_hit_at_5 = anchor_hits / anchor_total if anchor_total else 0.0
    cross_hit_at_5 = cross_hits / cross_total if cross_total else 0.0
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

    # ── gate evaluation ──────────────────────────────────
    anchor_pass = anchor_hit_at_5 >= 0.40
    cross_pass = cross_hit_at_5 >= 0.50
    latency_pass = avg_latency < 0.2

    if anchor_pass and cross_pass:
        overall = "PASS"
    elif anchor_hit_at_5 >= 0.30 and cross_hit_at_5 >= 0.30:
        overall = "CONDITIONAL"
    else:
        overall = "BLOCKED"

    result.update(
        {
            "status": overall,
            "query_count": anchor_total,
            "anchor_hit_at_5": round(anchor_hit_at_5, 4),
            "cross_paper_hit_at_5": round(cross_hit_at_5, 4),
            "avg_latency_s": round(avg_latency, 4),
            "fallback_used": False,
            "entity_count": entity_count,
            "embed_dim": embed_dim,
            "details": details,
            "gate": {
                "anchor_pass": anchor_pass,
                "cross_pass": cross_pass,
                "latency_pass": latency_pass,
                "overall": overall,
            },
        }
    )

    print(f"\n[anchor-eval] anchor_hit@5={anchor_hit_at_5:.3f}  cross@5={cross_hit_at_5:.3f}  avg_lat={avg_latency:.3f}s")
    print(f"[anchor-eval] Gate: {overall}")

    _write_anchor_eval(output_dir, result)
    return result


def _write_anchor_eval(output_dir: Path, result: Dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "specter2_anchor_eval.json"
    md_path = output_dir / "specter2_anchor_eval.md"

    with open(json_path, "w") as f:
        json.dump(result, f, indent=2)

    gate = result.get("gate", {})
    overall = gate.get("overall", result.get("status", "BLOCKED"))
    icon = {"PASS": "✅", "CONDITIONAL": "⚠️", "BLOCKED": "❌"}.get(overall, "❌")

    md = f"""# SPECTER2 Anchor Eval

- status: {icon} **{overall}**
- ts: {result["ts"]}
- collection: `{result["collection"]}`
- query_count: {result["query_count"]}

## Metrics

| metric | value | threshold | pass |
|---|---|---|---|
| anchor_hit_at_5 | {result["anchor_hit_at_5"]:.4f} | >= 0.40 | {"✅" if gate.get("anchor_pass") else "❌"} |
| cross_paper_hit_at_5 | {result["cross_paper_hit_at_5"]:.4f} | >= 0.50 | {"✅" if gate.get("cross_pass") else "❌"} |
| avg_latency_s | {result["avg_latency_s"]:.4f} | < 0.200 | {"✅" if gate.get("latency_pass") else "❌"} |
| fallback_used | {result.get("fallback_used", False)} | false | {"✅" if not result.get("fallback_used") else "❌"} |

"""
    if result.get("error"):
        md += f"## Error\n\n```\n{result['error']}\n```\n"
    elif result.get("details"):
        md += "## Query Details\n\n| query_id | family | anchor | cross | latency_s |\n|---|---|---|---|---|\n"
        for d in result["details"]:
            md += f"| {d['query_id']} | {d['family']} | {'✓' if d['anchor_hit'] else '✗'} | {'✓' if d['cross_paper_hit'] else '✗'} | {d['latency_s']} |\n"

    with open(md_path, "w") as f:
        f.write(md)

    print(f"[anchor-eval] Written: {json_path}")
    print(f"[anchor-eval] Written: {md_path}")


# ──────────────────────────────────────────────────────────
# main
# ──────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="SPECTER2 isolated embedding worker")
    p.add_argument("--mode", choices=["probe", "anchor-eval", "all"], default="all")
    p.add_argument("--milvus-host", default="localhost")
    p.add_argument("--milvus-port", type=int, default=19530)
    p.add_argument("--output-dir", default="artifacts/benchmarks/v2_2_1")
    p.add_argument("--top-k", type=int, default=5)
    return p.parse_args()


def main():
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    probe_result = None

    if args.mode in ("probe", "all"):
        print("\n=== SPECTER2 Environment Probe ===")
        probe_result = run_probe(output_dir)
        if probe_result["status"] != "PASS" and args.mode == "all":
            print("[main] Probe BLOCKED — skipping anchor-eval", file=sys.stderr)
            sys.exit(1)

    if args.mode in ("anchor-eval", "all"):
        print("\n=== SPECTER2 Anchor Eval ===")
        anchor_result = run_anchor_eval(
            output_dir=output_dir,
            milvus_host=args.milvus_host,
            milvus_port=args.milvus_port,
            top_k=args.top_k,
            probe_result=probe_result,
        )
        overall = anchor_result.get("gate", {}).get("overall", "BLOCKED")
        if overall == "BLOCKED":
            print(f"[main] Anchor eval BLOCKED.", file=sys.stderr)
            sys.exit(1)

    print("\n[main] Done.")


if __name__ == "__main__":
    main()
