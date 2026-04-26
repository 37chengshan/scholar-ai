#!/usr/bin/env python
"""Schema-aware preflight gate for Academic RAG v2.1.1 retrieval.

Blocks answer benchmark when any of the following occurs:
- vector dimension mismatch
- illegal branch->collection mapping
- unsupported field type in search output parsing
- missing collection/vector schema
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Literal

ROOT = Path(__file__).resolve().parent.parent
API_ROOT = ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.config import normalize_embedding_model_name, settings
from app.core.embedding.factory import get_embedding_service
from app.core.milvus_service import get_milvus_service
from app.core.multimodal_search_service import get_multimodal_search_service
from app.core.retrieval_branch_registry import (
    RetrievalPreflightError,
    assert_dim_match,
    ensure_branch_collection_allowed,
    get_qwen_collection,
    is_branch_enabled,
)
from app.core.vector_store_repository import get_vector_store_repository
from app.models.retrieval import SearchConstraints


StageName = Literal["raw", "rule", "llm"]
BranchName = Literal["qwen", "specter2", "all"]


def _stage_list(stage: str) -> list[StageName]:
    if stage == "all":
        return ["raw", "rule", "llm"]
    return [stage]  # type: ignore[return-value]


def _branch_list(branch: str) -> list[BranchName]:
    if branch == "all":
        return ["qwen", "specter2"]
    return [branch]  # type: ignore[return-value]


def _default_out_paths() -> tuple[Path, Path]:
    out_dir = ROOT / "artifacts" / "benchmarks" / "v2_1_20"
    return out_dir / "preflight_v2_1_1.json", out_dir / "preflight_v2_1_1.md"


def _effective_collection(dataset_profile: str, stage: StageName, branch: BranchName) -> str:
    if branch == "qwen":
        if dataset_profile == "v2.1":
            return get_qwen_collection(stage)
    return settings.MILVUS_COLLECTION_CONTENTS_V2


def _check_embedding(query: str) -> dict[str, Any]:
    service = get_embedding_service()
    service.load_model()
    vec = service.encode_text(query)
    dim = len(vec) if isinstance(vec, list) else 0
    model = normalize_embedding_model_name(settings.EMBEDDING_MODEL)
    return {
        "embedding_model": model,
        "query_dim": dim,
        "vector_preview": vec[:5] if isinstance(vec, list) else [],
        "_vector": vec if isinstance(vec, list) else [],
    }


def _safe_output_fields_check(collection_name: str, strict_schema: bool, safe_output_fields_only: bool) -> dict[str, Any]:
    milvus = get_milvus_service()
    collection = milvus.get_collection(collection_name)
    full_safe = milvus.resolve_safe_output_fields(collection, allow_raw_data=True)
    minimal_safe = milvus.resolve_safe_output_fields(collection, allow_raw_data=False)

    if safe_output_fields_only:
        chosen = minimal_safe
    else:
        chosen = full_safe

    if strict_schema and not chosen:
        raise RetrievalPreflightError(
            f"No legal output fields for collection={collection_name} under strict schema mode"
        )

    return {
        "full_safe_output_fields": full_safe,
        "minimal_safe_output_fields": minimal_safe,
        "chosen_output_fields": chosen,
    }


def _run_dense_smoke(
    *,
    branch: BranchName,
    stage: StageName,
    collection: str,
    query_vec: list[float],
    query_dim: int,
    user_id: str,
) -> dict[str, Any]:
    milvus = get_milvus_service()
    settings.MILVUS_COLLECTION_CONTENTS_V2 = collection
    coll = milvus.get_collection(collection)
    coll_dim = milvus.inspect_collection_vector_dim(coll, vector_field="embedding")

    ensure_branch_collection_allowed(branch, collection)
    assert_dim_match(
        branch=branch,
        model=settings.EMBEDDING_MODEL,
        collection=collection,
        vector_field="embedding",
        query_dim=query_dim,
        collection_dim=coll_dim,
    )

    constraints = SearchConstraints(user_id=user_id, content_types=["text"])
    hits = milvus.search_contents_v2(
        embedding=query_vec,
        user_id=user_id,
        content_type="text",
        top_k=1,
        constraints=constraints,
        branch=branch,
        model_name=settings.EMBEDDING_MODEL,
        vector_field="embedding",
    )

    return {
        "stage": stage,
        "branch": branch,
        "collection": collection,
        "query_dim": query_dim,
        "collection_dim": coll_dim,
        "top1_result_count": len(hits),
    }


def _run_sparse_smoke(query: str, user_id: str) -> dict[str, Any]:
    repo = get_vector_store_repository()
    constraints = SearchConstraints(user_id=user_id, content_types=["text"])
    rows = repo.search_sparse(
        query=query,
        user_id=user_id,
        content_type="text",
        top_k=1,
        constraints=constraints,
        prefetch_limit=50,
    )
    return {"top1_result_count": len(rows)}


def _run_hybrid_and_reranker_smoke(query: str, user_id: str) -> dict[str, Any]:
    service = get_multimodal_search_service()
    base = {}

    dense_only = awaitable_search(service, query, user_id, use_reranker=False)
    reranked = awaitable_search(service, query, user_id, use_reranker=True)

    base["hybrid_dense_sparse"] = {
        "dense_only_count": len(dense_only.get("results") or []),
        "reranked_count": len(reranked.get("results") or []),
    }
    diag = reranked.get("reranker_diagnostics") or {}
    base["reranker_smoke"] = {
        "reranker_used": bool(diag.get("reranker_used", False)),
        "rerank_input_count": int(diag.get("rerank_input_count") or 0),
        "rerank_output_count": int(diag.get("rerank_output_count") or 0),
        "rerank_changed_order": bool(diag.get("rerank_changed_order", False)),
        "reranker_scores_present": bool(diag.get("reranker_scores_present", False)),
        "pre_rerank_top_ids": diag.get("pre_rerank_top_ids") or [],
        "post_rerank_top_ids": diag.get("post_rerank_top_ids") or [],
    }
    return base


def awaitable_search(service: Any, query: str, user_id: str, use_reranker: bool) -> dict[str, Any]:
    import asyncio

    async def _run() -> dict[str, Any]:
        return await service.search(
            query=query,
            paper_ids=[],
            user_id=user_id,
            top_k=10,
            use_reranker=use_reranker,
            content_types=["text"],
        )

    return asyncio.run(_run())


def _to_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Retrieval Preflight v2.1.1")
    lines.append("")
    lines.append(f"- Overall Status: {report['overall_status']}")
    lines.append(f"- Dataset Profile: {report['dataset_profile']}")
    lines.append("")

    lines.append("## Dense Smoke")
    lines.append("")
    lines.append("| stage | branch | collection | query_dim | collection_dim | top1_count | status |")
    lines.append("|---|---|---|---:|---:|---:|---|")
    for row in report.get("dense_smoke", []):
        status = "PASS" if row.get("ok") else "FAIL"
        lines.append(
            f"| {row.get('stage')} | {row.get('branch')} | {row.get('collection')} | "
            f"{row.get('query_dim')} | {row.get('collection_dim')} | {row.get('top1_result_count')} | {status} |"
        )

    lines.append("")
    lines.append("## Output Fields")
    lines.append("")
    for row in report.get("output_fields", []):
        lines.append(f"- {row.get('collection')}: chosen={row.get('chosen_output_fields')} minimal={row.get('minimal_safe_output_fields')}")

    lines.append("")
    lines.append("## Hybrid/Reranker Smoke")
    lines.append("")
    hybrid = report.get("hybrid_smoke", {})
    rerank = report.get("reranker_smoke", {})
    lines.append(f"- dense_only_count: {hybrid.get('dense_only_count', 0)}")
    lines.append(f"- reranked_count: {hybrid.get('reranked_count', 0)}")
    lines.append(f"- reranker_used: {rerank.get('reranker_used', False)}")
    lines.append(f"- rerank_changed_order: {rerank.get('rerank_changed_order', False)}")
    lines.append(f"- reranker_scores_present: {rerank.get('reranker_scores_present', False)}")

    if report.get("errors"):
        lines.append("")
        lines.append("## Errors")
        lines.append("")
        for err in report["errors"]:
            lines.append(f"- {err}")

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Schema-aware retrieval preflight")
    parser.add_argument("--dataset-profile", default="v2.1")
    parser.add_argument("--stage", choices=["raw", "rule", "llm", "all"], default="all")
    parser.add_argument("--branch", choices=["qwen", "specter2", "all"], default="qwen")
    parser.add_argument("--strict-schema", action="store_true")
    parser.add_argument("--safe-output-fields-only", action="store_true")
    parser.add_argument("--smoke-user-id", default="preflight-user")
    parser.add_argument("--output-json", default="")
    parser.add_argument("--output-md", default="")
    args = parser.parse_args()

    default_json, default_md = _default_out_paths()
    output_json = Path(args.output_json) if args.output_json else default_json
    output_md = Path(args.output_md) if args.output_md else default_md
    output_json.parent.mkdir(parents=True, exist_ok=True)

    report: dict[str, Any] = {
        "overall_status": "PASS",
        "dataset_profile": args.dataset_profile,
        "stage": args.stage,
        "branch": args.branch,
        "strict_schema": bool(args.strict_schema),
        "safe_output_fields_only": bool(args.safe_output_fields_only),
        "embedding": {},
        "dense_smoke": [],
        "output_fields": [],
        "sparse_smoke": {},
        "hybrid_smoke": {},
        "reranker_smoke": {},
        "errors": [],
    }

    query = "preflight retrieval smoke query"

    try:
        emb = _check_embedding(query)
        full_query_vector = [float(v) for v in emb.pop("_vector", [])]
        report["embedding"] = emb
        query_dim = int(emb.get("query_dim") or 0)
        if query_dim <= 0:
            raise RetrievalPreflightError("Embedding check failed: query vector dim <= 0")

        for branch in _branch_list(args.branch):
            if branch != "all" and not is_branch_enabled(branch):
                raise RetrievalPreflightError(
                    f"Branch disabled: branch={branch}. Specter2 dense branch is disabled in v2.1.1"
                )

            if branch == "specter2":
                # Always blocked in v2.1.1 unless dedicated mapping exists.
                raise RetrievalPreflightError(
                    "specter2 branch requested but no dedicated specter2 collections are configured"
                )

            for stage in _stage_list(args.stage):
                collection = _effective_collection(args.dataset_profile, stage, branch)

                output_check = _safe_output_fields_check(
                    collection,
                    strict_schema=bool(args.strict_schema),
                    safe_output_fields_only=bool(args.safe_output_fields_only),
                )
                report["output_fields"].append({"collection": collection, **output_check})

                dense = _run_dense_smoke(
                    branch=branch,
                    stage=stage,
                    collection=collection,
                    query_vec=full_query_vector,
                    query_dim=query_dim,
                    user_id=args.smoke_user_id,
                )
                dense["ok"] = True
                report["dense_smoke"].append(dense)

        report["sparse_smoke"] = _run_sparse_smoke(query, args.smoke_user_id)
        hr = _run_hybrid_and_reranker_smoke(query, args.smoke_user_id)
        report["hybrid_smoke"] = hr.get("hybrid_dense_sparse", {})
        report["reranker_smoke"] = hr.get("reranker_smoke", {})

    except Exception as exc:
        report["overall_status"] = "FAIL"
        report["errors"].append(str(exc))

    output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md.write_text(_to_markdown(report), encoding="utf-8")

    print(f"preflight_json={output_json}")
    print(f"preflight_md={output_md}")
    print(f"overall_status={report['overall_status']}")

    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
