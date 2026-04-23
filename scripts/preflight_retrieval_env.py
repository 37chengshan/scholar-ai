#!/usr/bin/env python
"""Preflight checks for the formal retrieval benchmark environment."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
API_ROOT = ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.config import (
    canonical_embedding_dimension,
    normalize_embedding_model_name,
    normalize_reranker_model_name,
    resolve_model_stack,
    settings,
)
from app.core.embedding.factory import get_embedding_service
from app.core.milvus_service import get_milvus_service
from app.core.qdrant_service import get_qdrant_service
from app.models.retrieval import SearchConstraints


def _check_embedding(model_stack: str) -> dict[str, Any]:
    configured_model = settings.EMBEDDING_MODEL
    normalized_model = normalize_embedding_model_name(configured_model)
    expected_dimension = canonical_embedding_dimension(
        normalized_model,
        settings.EMBEDDING_DIMENSION,
    )
    service = get_embedding_service()
    service.load_model()
    vector = service.encode_text("retrieval preflight query")
    vector_length = len(vector) if isinstance(vector, list) else 0
    dimension_matches = bool(vector_length) and vector_length == expected_dimension

    expected_stack = resolve_model_stack(
        model_stack,
        settings.EMBEDDING_MODEL,
        settings.RERANKER_MODEL,
    )

    return {
        "name": "embedding",
        "ok": dimension_matches,
        "details": {
            "configured_model": configured_model,
            "normalized_model": normalized_model,
            "resolved_stack": expected_stack,
            "service_class": service.__class__.__name__,
            "vector_length": vector_length,
            "expected_dimension": expected_dimension,
            "configured_dimension": settings.EMBEDDING_DIMENSION,
            "dimension_matches": dimension_matches,
        },
        "embedding": vector,
    }


def _check_model_stack(model_stack: str) -> dict[str, Any]:
    resolved_stack = resolve_model_stack(
        model_stack,
        settings.EMBEDDING_MODEL,
        settings.RERANKER_MODEL,
    )
    expected_pairs = {
        "bge_dual": ("bge-m3", "bge-reranker"),
        "qwen_dual": ("qwen3-vl-2b", "qwen3-vl-reranker"),
    }
    normalized_embedding = normalize_embedding_model_name(settings.EMBEDDING_MODEL)
    normalized_reranker = normalize_reranker_model_name(settings.RERANKER_MODEL)

    if model_stack in expected_pairs:
        expected_embedding, expected_reranker = expected_pairs[model_stack]
        ok = normalized_embedding == expected_embedding and normalized_reranker == expected_reranker
    else:
        ok = True

    return {
        "name": "model_stack",
        "ok": ok,
        "details": {
            "requested_stack": model_stack,
            "resolved_stack": resolved_stack,
            "embedding_model": normalized_embedding,
            "reranker_model": normalized_reranker,
            "vector_backend": settings.VECTOR_STORE_BACKEND,
        },
    }


def _check_milvus(
    embedding: list[float],
    *,
    collection_name: str,
    smoke_user_id: str,
) -> dict[str, Any]:
    milvus = get_milvus_service()
    lite_available = importlib.util.find_spec("milvus_lite") is not None
    milvus.connect()
    has_collection = milvus.has_collection(collection_name)
    created_collection = False
    smoke_results = []

    if not has_collection:
        milvus.create_collection_v2()
        has_collection = milvus.has_collection(collection_name)
        created_collection = has_collection

    if has_collection:
        smoke_results = milvus.search_contents_v2(
            embedding=embedding,
            user_id=smoke_user_id,
            content_type="text",
            top_k=1,
            constraints=SearchConstraints(user_id=smoke_user_id),
        )

    return {
        "name": "vector_store",
        "ok": has_collection,
        "details": {
            "backend": "milvus",
            "host": settings.MILVUS_HOST,
            "port": settings.MILVUS_PORT,
            "collection": collection_name,
            "collection_exists": has_collection,
            "collection_created": created_collection,
            "milvus_lite_available": lite_available,
            "smoke_query_executed": has_collection,
            "smoke_result_count": len(smoke_results),
        },
    }


def _check_qdrant(
    embedding: list[float],
    *,
    collection_name: str,
    smoke_user_id: str,
) -> dict[str, Any]:
    qdrant = get_qdrant_service()
    client = qdrant._get_client()
    collection_exists = False

    if hasattr(client, "collection_exists"):
        collection_exists = bool(client.collection_exists(collection_name))
    elif hasattr(client, "get_collection"):
        try:
            client.get_collection(collection_name)
            collection_exists = True
        except Exception:
            collection_exists = False

    smoke_results: list[dict[str, Any]] = []
    if collection_exists:
        smoke_results = qdrant.search(
            embedding=embedding,
            user_id=smoke_user_id,
            content_type="text",
            top_k=1,
            constraints=SearchConstraints(user_id=smoke_user_id),
        )

    return {
        "name": "vector_store",
        "ok": collection_exists,
        "details": {
            "backend": "qdrant",
            "url": settings.QDRANT_URL,
            "collection": collection_name,
            "collection_exists": collection_exists,
            "smoke_query_executed": collection_exists,
            "smoke_result_count": len(smoke_results),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Preflight retrieval benchmark environment")
    parser.add_argument(
        "--backend",
        choices=["milvus", "qdrant"],
        default=settings.VECTOR_STORE_BACKEND,
        help="Vector backend to validate",
    )
    parser.add_argument(
        "--model-stack",
        choices=["bge_dual", "qwen_dual", "manual"],
        default=settings.RETRIEVAL_MODEL_STACK,
        help="Expected benchmark model stack",
    )
    parser.add_argument(
        "--collection",
        default="",
        help="Optional explicit vector collection name",
    )
    parser.add_argument(
        "--smoke-user-id",
        default="preflight-user",
        help="User id used for isolation smoke query",
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "artifacts" / "benchmarks" / "real" / "preflight_report.json"),
        help="Where to write the JSON report",
    )
    args = parser.parse_args()

    checks: list[dict[str, Any]] = []
    exit_code = 0

    try:
        checks.append(_check_model_stack(args.model_stack))
        embedding_check = _check_embedding(args.model_stack)
        embedding = embedding_check.pop("embedding")
        checks.append(embedding_check)
    except Exception as exc:
        checks.append(
            {
                "name": "embedding",
                "ok": False,
                "details": {"error": str(exc)},
            }
        )
        embedding = []
        exit_code = 1

    try:
        resolved_collection = args.collection
        if not resolved_collection:
            resolved_collection = (
                settings.QDRANT_COLLECTION_CONTENTS_V2
                if args.backend == "qdrant"
                else settings.MILVUS_COLLECTION_CONTENTS_V2
            )

        if args.backend == "qdrant":
            checks.append(
                _check_qdrant(
                    embedding,
                    collection_name=resolved_collection,
                    smoke_user_id=args.smoke_user_id,
                )
            )
        else:
            checks.append(
                _check_milvus(
                    embedding,
                    collection_name=resolved_collection,
                    smoke_user_id=args.smoke_user_id,
                )
            )
    except Exception as exc:
        checks.append(
            {
                "name": "vector_store",
                "ok": False,
                "details": {
                    "backend": args.backend,
                    "error": str(exc),
                },
            }
        )
        exit_code = 1

    if not all(check.get("ok") for check in checks):
        exit_code = 1

    report = {
        "backend": args.backend,
        "ok": exit_code == 0,
        "checks": checks,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
