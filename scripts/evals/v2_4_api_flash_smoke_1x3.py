#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from pymilvus import Collection, connections

from app.core.model_gateway import create_embedding_provider
from app.core.model_gateway.active_providers import GLM45AirProvider, Qwen3VLRerankProvider

from scripts.evals.v2_4_common import (
    DEFAULT_OUTPUT_DIR,
    OFFICIAL_MODEL,
    OFFICIAL_OUTPUT_FIELDS,
    OFFICIAL_PROVIDER,
    stage_collection_name,
    write_json,
    write_markdown,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="v2.4 API flash smoke 1x3")
    p.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    p.add_argument("--provider", default=OFFICIAL_PROVIDER)
    p.add_argument("--model", default=OFFICIAL_MODEL)
    p.add_argument("--collection-suffix", default="v2_4")
    p.add_argument("--query", default="Summarize the main method and provide evidence")
    p.add_argument("--milvus-host", default="localhost")
    p.add_argument("--milvus-port", type=int, default=19530)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    report: Dict[str, Any] = {
        "query": args.query,
        "provider": args.provider,
        "model": args.model,
        "stages": {},
        "fallback_used": False,
        "deprecated_branch_used": False,
        "status": "BLOCKED",
        "error": None,
    }

    try:
        provider = create_embedding_provider(args.provider, args.model)
        query_vec = provider.embed_texts([args.query])[0]

        connections.connect(alias="v24_smoke", host=args.milvus_host, port=args.milvus_port)

        reranker = Qwen3VLRerankProvider()
        llm = GLM45AirProvider()

        for stage in ["raw", "rule", "llm"]:
            name = stage_collection_name(stage, args.collection_suffix)
            col = Collection(name, using="v24_smoke")
            col.load()
            res = col.search(
                data=[query_vec],
                anns_field="embedding",
                param={"metric_type": "COSINE", "params": {"nprobe": 10}},
                limit=5,
                output_fields=OFFICIAL_OUTPUT_FIELDS,
            )
            hits = res[0] if res else []
            docs: List[str] = []
            evidence: List[Dict[str, Any]] = []
            for hit in hits:
                fields = hit.fields if hasattr(hit, "fields") and hit.fields else {}
                docs.append(str(fields.get("content_data") or ""))
                evidence.append(
                    {
                        "source_chunk_id": str(fields.get("source_chunk_id") or ""),
                        "paper_id": str(fields.get("paper_id") or ""),
                        "page_num": fields.get("page_num"),
                        "section": str(fields.get("section") or ""),
                    }
                )

            reranked = reranker.rerank(args.query, docs, top_k=min(3, len(docs))) if docs else []
            answer = llm.generate(
                "\\n".join([
                    f"query: {args.query}",
                    "evidence:",
                    *[f"- {d[:300]}" for d in docs[:3]],
                ]),
                max_tokens=256,
            )

            stage_ok = bool(hits) and bool(reranked) and bool(answer)
            if not stage_ok:
                raise RuntimeError(f"smoke_stage_failed:{stage}")

            report["stages"][stage] = {
                "collection": name,
                "hits": len(hits),
                "reranked": len(reranked),
                "evidence_pack": evidence[:3],
                "answer_preview": answer[:300],
                "status": "PASS" if stage_ok else "BLOCKED",
            }

        report["status"] = "PASS"

    except Exception as exc:
        report["status"] = "BLOCKED"
        report["error"] = str(exc)

    write_json(out_dir / "api_flash_smoke_1x3.json", report)
    lines = [
        f"- query: {report['query']}",
        f"- fallback_used: {report['fallback_used']}",
        f"- deprecated_branch_used: {report['deprecated_branch_used']}",
        f"- status: {report['status']}",
        "",
        "| stage | hits | reranked | status |",
        "|---|---:|---:|---|",
    ]
    for stage, stat in report.get("stages", {}).items():
        lines.append(f"| {stage} | {stat.get('hits',0)} | {stat.get('reranked',0)} | {stat.get('status')} |")
    if report.get("error"):
        lines.extend(["", "## Error", "", "```", str(report["error"]), "```"])
    write_markdown(out_dir / "api_flash_smoke_1x3.md", "v2.4 API Flash Smoke 1x3", lines)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
