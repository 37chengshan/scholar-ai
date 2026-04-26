#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from pymilvus import Collection, connections

from app.core.model_gateway import create_embedding_provider
from app.core.model_gateway.active_providers import GLM45AirProvider, Qwen3VLRerankProvider
from app.core.rag_runtime_profile import OFFICIAL_RUNTIME_PROFILE

from scripts.evals.v2_4_common import (
    DEFAULT_OUTPUT_DIR,
    OFFICIAL_MODEL,
    OFFICIAL_OUTPUT_FIELDS,
    OFFICIAL_PROVIDER,
    ensure_query_dim_matches_collection_dim,
    read_json,
    stage_collection_name,
    write_json,
    write_markdown,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="v2.4 API flash preflight")
    p.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    p.add_argument("--provider", default=OFFICIAL_PROVIDER)
    p.add_argument("--model", default=OFFICIAL_MODEL)
    p.add_argument("--collection-suffix", default="v2_4")
    p.add_argument("--milvus-host", default="localhost")
    p.add_argument("--milvus-port", type=int, default=19530)
    return p.parse_args()


def _collection_dim(col: Collection) -> int:
    for f in col.schema.fields:
        if getattr(f, "name", "") == "embedding":
            return int((getattr(f, "params", {}) or {}).get("dim", 0))
    return 0


def _run_search(col: Collection, vec: List[float], output_fields: List[str]) -> List[Any]:
    return col.search(
        data=[vec],
        anns_field="embedding",
        param={"metric_type": "COSINE", "params": {"nprobe": 10}},
        limit=3,
        output_fields=output_fields,
    )


def main() -> int:
    args = parse_args()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    report: Dict[str, Any] = {
        "runtime_profile": OFFICIAL_RUNTIME_PROFILE,
        "provider": args.provider,
        "model": args.model,
        "fallback_used": False,
        "deprecated_branch_used": False,
        "query_dim": 0,
        "expected_dim": 0,
        "stages": {},
        "hydration_ok": False,
        "rerank_contract_ok": False,
        "llm_contract_ok": False,
        "status": "BLOCKED",
        "error": None,
    }

    try:
        probe = read_json(out_dir / "provider_probe.json")
        if str(probe.get("status") or "") != "PASS":
            raise RuntimeError("provider_probe_not_pass")
        report["expected_dim"] = int(probe.get("dimension") or 0)

        provider = create_embedding_provider(args.provider, args.model)
        query_vec = provider.embed_texts(["preflight query"])[0]
        report["query_dim"] = len(query_vec)

        connections.connect(alias="v24_preflight", host=args.milvus_host, port=args.milvus_port)

        hydration_ok = True
        for stage in ["raw", "rule", "llm"]:
            name = stage_collection_name(stage, args.collection_suffix)
            col = Collection(name, using="v24_preflight")
            col.load()
            dim = _collection_dim(col)
            ensure_query_dim_matches_collection_dim(report["query_dim"], dim)

            id_only = _run_search(col, query_vec, output_fields=[])
            id_only_ok = bool(id_only and id_only[0])

            minimal = _run_search(col, query_vec, output_fields=OFFICIAL_OUTPUT_FIELDS)
            minimal_ok = bool(minimal and minimal[0])

            first_hit = minimal[0][0] if minimal and minimal[0] else None
            first_fields = {}
            if first_hit is not None and hasattr(first_hit, "fields") and first_hit.fields:
                first_fields = first_hit.fields
            hydration_stage_ok = all(str(first_fields.get(k, "")) for k in ["source_chunk_id", "paper_id", "content_data"])
            hydration_ok = hydration_ok and hydration_stage_ok

            report["stages"][stage] = {
                "collection": name,
                "collection_dim": dim,
                "id_only_search_ok": id_only_ok,
                "minimal_output_fields_ok": minimal_ok,
                "hydration_ok": hydration_stage_ok,
                "official_output_fields": OFFICIAL_OUTPUT_FIELDS,
            }

            if not (id_only_ok and minimal_ok and hydration_stage_ok):
                raise RuntimeError(f"preflight_stage_failed:{stage}")

        report["hydration_ok"] = hydration_ok

        reranker = Qwen3VLRerankProvider()
        reranked = reranker.rerank("q", ["doc1", "doc2"], top_k=1)
        report["rerank_contract_ok"] = bool(reranked and "score" in reranked[0])

        llm = GLM45AirProvider()
        out = llm.generate("hello", max_tokens=16)
        report["llm_contract_ok"] = bool(out)

        if not report["rerank_contract_ok"]:
            raise RuntimeError("rerank_contract_failed")
        if not report["llm_contract_ok"]:
            raise RuntimeError("llm_contract_failed")

        report["status"] = "PASS"

    except Exception as exc:
        report["status"] = "BLOCKED"
        report["error"] = str(exc)

    write_json(out_dir / "api_flash_preflight.json", report)
    lines = [
        f"- runtime_profile: {report['runtime_profile']}",
        f"- query_dim: {report['query_dim']}",
        f"- expected_dim: {report['expected_dim']}",
        f"- fallback_used: {report['fallback_used']}",
        f"- deprecated_branch_used: {report['deprecated_branch_used']}",
        f"- hydration_ok: {report['hydration_ok']}",
        f"- rerank_contract_ok: {report['rerank_contract_ok']}",
        f"- llm_contract_ok: {report['llm_contract_ok']}",
        f"- status: {report['status']}",
        "",
        "| stage | collection_dim | id_only_search_ok | minimal_output_fields_ok | hydration_ok |",
        "|---|---:|---|---|---|",
    ]
    for stage, stat in report.get("stages", {}).items():
        lines.append(
            f"| {stage} | {stat.get('collection_dim',0)} | {stat.get('id_only_search_ok')} | {stat.get('minimal_output_fields_ok')} | {stat.get('hydration_ok')} |"
        )
    if report.get("error"):
        lines.extend(["", "## Error", "", "```", str(report["error"]), "```"])
    write_markdown(out_dir / "api_flash_preflight.md", "v2.4 API Flash Preflight", lines)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
