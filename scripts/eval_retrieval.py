#!/usr/bin/env python
"""Retrieval evaluation harness with planner/evidence metrics.

Usage:
    python scripts/eval_retrieval.py --golden tests/evals/golden_queries.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import sys

backend_path = Path(__file__).parent.parent / "apps" / "api"
if backend_path.exists():
    sys.path.insert(0, str(backend_path))

from app.core.chunk_identity import spans_overlap
from app.core.section_normalizer import canonicalize_section_name, normalize_section_path, serialize_section_path


def _avg(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _p95(values: List[float]) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = max(int(len(sorted_values) * 0.95) - 1, 0)
    return sorted_values[index]


def calculate_recall_at_k(retrieved_ids: List[str], expected_ids: List[str], k: int) -> float:
    if not expected_ids:
        return 0.0
    retrieved = set(retrieved_ids[:k])
    expected = set(expected_ids)
    return len(retrieved & expected) / len(expected)


def calculate_mrr(retrieved_ids: List[str], expected_ids: List[str]) -> float:
    if not expected_ids:
        return 0.0
    expected = set(expected_ids)
    for idx, item in enumerate(retrieved_ids, start=1):
        if item in expected:
            return 1.0 / idx
    return 0.0


def _to_int(value: object, default: int = 0) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _normalize_section_value(section_value: object) -> str:
    raw = str(section_value or "").strip()
    if not raw:
        return ""
    normalized_tokens = normalize_section_path(raw)
    if normalized_tokens:
        return normalized_tokens[-1]
    return canonicalize_section_name(raw)


def _extract_result_section(result: Dict[str, Any]) -> str:
    normalized = result.get("normalized_section_leaf") or result.get("normalized_section_path")
    if normalized:
        value = str(normalized)
        return value.split("/")[-1]

    raw_data = result.get("raw_data") or {}
    if isinstance(raw_data, dict):
        for key in ("normalized_section_leaf", "normalized_section_path", "section_path", "raw_section_path"):
            if raw_data.get(key):
                value = str(raw_data.get(key))
                return _normalize_section_value(value.split("/")[-1] if "/" in value else value)

    return _normalize_section_value(result.get("section") or result.get("content_section"))


def calculate_section_hit_rate(results: List[Dict[str, Any]], expected_sections: List[str]) -> float:
    if not expected_sections:
        return 0.0
    expected = {_normalize_section_value(item) for item in expected_sections if _normalize_section_value(item)}
    if not expected:
        return 0.0
    retrieved = {_extract_result_section(item) for item in results[:10] if _extract_result_section(item)}
    return len(retrieved & expected) / len(expected)


def _extract_chunk_id(result: Dict[str, Any]) -> str:
    raw_data = result.get("raw_data") or {}
    if isinstance(raw_data, dict) and raw_data.get("chunk_id"):
        return str(raw_data.get("chunk_id"))
    return str(result.get("chunk_id") or result.get("source_id") or result.get("id") or "")


def _extract_anchor_text(result: Dict[str, Any]) -> str:
    raw_data = result.get("raw_data") or {}
    if isinstance(raw_data, dict) and raw_data.get("anchor_text"):
        return str(raw_data.get("anchor_text"))
    return str(result.get("anchor_text") or result.get("text") or result.get("content_data") or "")


def _normalize_anchor_text(value: str) -> str:
    normalized = re.sub(r"\s+", " ", (value or "").strip().lower())
    return normalized


def _extract_chunk_span(result: Dict[str, Any]) -> Dict[str, Any]:
    raw_data = result.get("raw_data") or {}
    raw_section_path = ""
    if isinstance(raw_data, dict):
        raw_section_path = str(
            raw_data.get("normalized_section_path")
            or raw_data.get("raw_section_path")
            or raw_data.get("section_path")
            or ""
        )
    if not raw_section_path:
        raw_section_path = str(result.get("normalized_section_path") or result.get("section") or "")

    normalized_tokens = normalize_section_path(raw_section_path)
    normalized_section_path = serialize_section_path(normalized_tokens)

    char_start = _to_int(result.get("char_start"))
    char_end = _to_int(result.get("char_end"))
    if isinstance(raw_data, dict):
        char_start = _to_int(raw_data.get("char_start"), char_start)
        char_end = _to_int(raw_data.get("char_end"), char_end)
        if not char_end and isinstance(raw_data.get("source_span"), dict):
            source_span = raw_data.get("source_span")
            char_start = _to_int(source_span.get("start_char"), char_start)
            char_end = _to_int(source_span.get("end_char"), char_end)
    if char_end <= char_start:
        inferred = len(_extract_anchor_text(result))
        char_end = char_start + max(inferred, 1)

    return {
        "chunk_id": _extract_chunk_id(result),
        "paper_id": str(result.get("paper_id") or ""),
        "page_num": _to_int(result.get("page_num") or result.get("page") or result.get("page_start")),
        "normalized_section_path": normalized_section_path,
        "char_start": char_start,
        "char_end": char_end,
        "anchor_text": _extract_anchor_text(result),
    }


def _normalize_expected_chunks(expected_chunks: List[Any]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for item in expected_chunks:
        if isinstance(item, str):
            normalized.append({"chunk_id": item})
            continue
        if not isinstance(item, dict):
            continue
        section_path = str(item.get("normalized_section_path") or item.get("section") or "")
        section_tokens = normalize_section_path(section_path)
        normalized.append(
            {
                "chunk_id": str(item.get("chunk_id") or item.get("id") or ""),
                "paper_id": str(item.get("paper_id") or ""),
                "page_num": _to_int(item.get("page_num") or item.get("page") or item.get("page_start")),
                "normalized_section_path": serialize_section_path(section_tokens),
                "char_start": _to_int(item.get("char_start")),
                "char_end": _to_int(item.get("char_end")),
                "anchor_text": str(item.get("anchor_text") or ""),
            }
        )
    return normalized


def calculate_chunk_match_metrics(results: List[Dict[str, Any]], expected_chunks: List[Any], k: int = 10) -> Dict[str, float]:
    if not expected_chunks:
        return {
            "chunk_hit_rate": 0.0,
            "exact_chunk_hit": 0.0,
            "overlap_chunk_hit": 0.0,
            "anchor_hit": 0.0,
        }

    expected = _normalize_expected_chunks(expected_chunks)
    retrieved = [_extract_chunk_span(item) for item in results[:k]]

    exact_hits = 0
    overlap_hits = 0
    anchor_hits = 0

    for expected_item in expected:
        expected_chunk_id = str(expected_item.get("chunk_id") or "")
        expected_anchor = _normalize_anchor_text(str(expected_item.get("anchor_text") or ""))
        expected_paper = str(expected_item.get("paper_id") or "")
        expected_page = _to_int(expected_item.get("page_num"))
        expected_section = str(expected_item.get("normalized_section_path") or "")
        expected_start = _to_int(expected_item.get("char_start"))
        expected_end = _to_int(expected_item.get("char_end"))

        matched_exact = False
        matched_overlap = False
        matched_anchor = False

        for retrieved_item in retrieved:
            if expected_chunk_id and retrieved_item["chunk_id"] == expected_chunk_id:
                matched_exact = True

            comparable_span = bool(expected_end > expected_start)
            same_scope = True
            if expected_paper and retrieved_item["paper_id"] and expected_paper != retrieved_item["paper_id"]:
                same_scope = False
            if expected_page and retrieved_item["page_num"] and expected_page != retrieved_item["page_num"]:
                same_scope = False
            if expected_section and retrieved_item["normalized_section_path"] and expected_section != retrieved_item["normalized_section_path"]:
                same_scope = False

            if comparable_span and same_scope:
                if spans_overlap(
                    expected_start,
                    expected_end,
                    _to_int(retrieved_item["char_start"]),
                    _to_int(retrieved_item["char_end"]),
                ):
                    matched_overlap = True

            if expected_anchor:
                retrieved_anchor = _normalize_anchor_text(str(retrieved_item["anchor_text"]))
                if retrieved_anchor and (
                    expected_anchor in retrieved_anchor or retrieved_anchor in expected_anchor
                ):
                    matched_anchor = True

        exact_hits += 1 if matched_exact else 0
        overlap_hits += 1 if matched_overlap else 0
        anchor_hits += 1 if matched_anchor else 0

    total = float(len(expected))
    any_hit = 1.0 if (exact_hits > 0 or overlap_hits > 0 or anchor_hits > 0) else 0.0
    return {
        "chunk_hit_rate": max(exact_hits, overlap_hits, anchor_hits) / total,
        "exact_chunk_hit": exact_hits / total,
        "overlap_chunk_hit": overlap_hits / total,
        "anchor_hit": anchor_hits / total,
        "any_chunk_hit": any_hit,
    }


def calculate_chunk_hit_rate(results: List[Dict[str, Any]], expected_chunks: List[Any], k: int = 10) -> float:
    return calculate_chunk_match_metrics(results, expected_chunks, k=k)["chunk_hit_rate"]


def calculate_section_mrr(results: List[Dict[str, Any]], expected_sections: List[str]) -> float:
    if not expected_sections:
        return 0.0
    normalized_expected = {_normalize_section_value(item) for item in expected_sections if _normalize_section_value(item)}
    for idx, result in enumerate(results[:10], start=1):
        section = _extract_result_section(result)
        if section in normalized_expected:
            return 1.0 / idx
    return 0.0


def classify_failure_bucket(
    results: List[Dict[str, Any]],
    expected_paper_ids: List[str],
    expected_sections: List[str],
    chunk_metrics: Dict[str, float],
    expected_chunks: List[Any],
) -> str:
    if not results:
        return "retrieval_miss"

    if not expected_paper_ids and not expected_sections and not expected_chunks:
        return "evaluation_mapping_error"

    expected_papers = {str(item) for item in expected_paper_ids if str(item)}
    paper_hit = not expected_papers or any(str(item.get("paper_id") or "") in expected_papers for item in results[:10])
    if not paper_hit:
        return "retrieval_miss"

    section_hit = calculate_section_hit_rate(results, expected_sections) > 0.0 if expected_sections else True
    if expected_sections and not section_hit:
        return "paper_hit_but_section_miss"

    chunk_hit = chunk_metrics.get("any_chunk_hit", 0.0) > 0.0
    if expected_chunks and not chunk_hit:
        return "section_hit_but_chunk_miss"

    return ""


def calculate_paper_hit_rate(results: List[Dict[str, Any]], expected_paper_ids: List[str], k: int = 5) -> float:
    if not expected_paper_ids:
        return 0.0
    hit_papers = {
        str(item.get("paper_id"))
        for item in results[:k]
        if item.get("paper_id") in set(expected_paper_ids)
    }
    return len(hit_papers) / len(expected_paper_ids)


def calculate_top5_cross_paper_completeness(results: List[Dict[str, Any]], expected_paper_ids: List[str]) -> float:
    return calculate_paper_hit_rate(results, expected_paper_ids, k=5)


def calculate_table_hit_rate(results: List[Dict[str, Any]], expected_table_refs: List[str]) -> float:
    if not expected_table_refs:
        return 0.0
    refs = {str(item.get("table_ref") or "") for item in results[:10]}
    refs.discard("")
    return len(refs & set(expected_table_refs)) / len(expected_table_refs)


def calculate_figure_hit_rate(results: List[Dict[str, Any]], expected_figure_refs: List[str]) -> float:
    if not expected_figure_refs:
        return 0.0
    refs = {str(item.get("figure_ref") or "") for item in results[:10]}
    refs.discard("")
    return len(refs & set(expected_figure_refs)) / len(expected_figure_refs)


def calculate_numeric_qa_exact_match(results: List[Dict[str, Any]], gold_triplets: List[Dict[str, Any]]) -> float:
    if not gold_triplets:
        return 0.0
    observed = {
        (
            str(item.get("method") or "").lower(),
            str(item.get("dataset") or "").lower(),
            str(item.get("metric_name") or "").lower(),
            str(item.get("score_value") or "").lower(),
        )
        for item in results[:10]
    }
    gold = {
        (
            str(item.get("method") or "").lower(),
            str(item.get("dataset") or "").lower(),
            str(item.get("metric") or item.get("metric_name") or "").lower(),
            str(item.get("value") or item.get("score_value") or "").lower(),
        )
        for item in gold_triplets
    }
    return 1.0 if gold and observed & gold else 0.0


def _mock_results(query_data: Dict[str, Any], query_type: str) -> Dict[str, Any]:
    expected_paper_ids = query_data.get("expected_paper_ids") or query_data.get("paper_ids") or []
    expected_sections = query_data.get("expected_sections") or []
    expected_chunks = query_data.get("expected_chunks")

    if expected_chunks:
        result_ids = list(expected_chunks)
    elif expected_paper_ids:
        # Keep deterministic behavior for unit tests.
        if query_type in {"cross_paper", "compare"} and len(expected_paper_ids) > 1:
            result_ids = [expected_paper_ids[0]]
        else:
            result_ids = list(expected_paper_ids)
    else:
        result_ids = ["mock-source-1"]

    results = []
    for idx, source_id in enumerate(result_ids[:10]):
        section = expected_sections[idx % len(expected_sections)] if expected_sections else "General"
        paper_id = source_id if source_id in expected_paper_ids else (expected_paper_ids[0] if expected_paper_ids else "mock-paper")
        normalized_section_tokens = normalize_section_path(section)
        normalized_section_path = serialize_section_path(normalized_section_tokens)
        anchor_text = f"Mock evidence for {query_data.get('query', '')}".strip()
        char_start = 0
        char_end = max(len(anchor_text), 1)
        chunk_id = source_id
        if not chunk_id.startswith("chunk_"):
            from app.core.chunk_identity import build_stable_chunk_id

            chunk_id = build_stable_chunk_id(
                paper_id=paper_id,
                page_num=1,
                normalized_section_path=normalized_section_path,
                char_start=char_start,
                char_end=char_end,
            )
        results.append(
            {
                "source_id": source_id,
                "id": source_id,
                "chunk_id": chunk_id,
                "paper_id": paper_id,
                "section": section,
                "normalized_section_path": normalized_section_path,
                "normalized_section_leaf": normalized_section_path.split("/")[-1] if normalized_section_path else "",
                "page_num": 1,
                "char_start": char_start,
                "char_end": char_end,
                "anchor_text": anchor_text,
                "content_type": "table" if query_type == "table" else "text",
                "paper_role": "result",
                "table_ref": "table-1" if query_type in {"table", "numeric", "compare"} else None,
                "figure_ref": "figure-1" if query_type == "figure" else None,
                "method": "method-a",
                "dataset": "cifar-10",
                "metric_name": "accuracy",
                "score_value": "96.2",
                "evidence_bundle_id": f"bundle-{idx}",
                "evidence_types": ["text", "table"] if query_type in {"table", "numeric", "compare"} else ["text"],
                "raw_data": {
                    "chunk_id": chunk_id,
                    "normalized_section_path": normalized_section_path,
                    "normalized_section_leaf": normalized_section_path.split("/")[-1] if normalized_section_path else "",
                    "char_start": char_start,
                    "char_end": char_end,
                    "anchor_text": anchor_text,
                },
            }
        )

    family = query_data.get("query_family") or query_type
    planner_queries = query_data.get("planner_queries") or [query_data.get("query", "")]

    return {
        "query_family": family,
        "planner_query_count": len(planner_queries),
        "decontextualized_query": query_data.get("decontextualized_query") or query_data.get("query", ""),
        "second_pass_used": bool(query_data.get("second_pass_used", False)),
        "second_pass_gain": float(query_data.get("second_pass_gain", 0.0)),
        "results": results,
    }


async def _run_single_query(
    service: Any,
    query_data: Dict[str, Any],
    *,
    user_id: str,
    paper_ids: List[str],
    use_reranker: bool,
    mock_mode: bool,
) -> Dict[str, Any]:
    query = query_data.get("query", "")
    query_type = query_data.get("query_type") or query_data.get("query_family")
    if not query_type:
        query_type = "compare" if len(paper_ids) > 1 else "fact"

    if mock_mode:
        return _mock_results(query_data, query_type)

    result = await service.search(
        query=query,
        paper_ids=paper_ids,
        user_id=user_id,
        top_k=10,
        use_reranker=use_reranker,
        content_types=query_data.get("content_types"),
    )
    return result


async def evaluate_retrieval(
    golden_queries_path: str,
    user_id: str = "eval-user",
    paper_ids_filter: Optional[List[str]] = None,
    mock_mode: bool = False,
    use_reranker: bool = False,
    dataset_label: str = "unknown",
    model_stack: str = "manual",
    run_label: str = "round1",
) -> Dict[str, Any]:
    with open(golden_queries_path, encoding="utf-8") as f:
        golden = json.load(f)

    service = None
    if not mock_mode:
        from app.core.multimodal_search_service import get_multimodal_search_service

        service = get_multimodal_search_service()

    metrics: Dict[str, List[float]] = {
        "recall_at_5": [],
        "recall_at_10": [],
        "mrr": [],
        "section_hit_rate": [],
        "multimodal_hit_rate": [],
        "paper_hit_rate": [],
        "planner_query_count": [],
        "second_pass_used": [],
        "second_pass_gain": [],
        "evidence_bundle_hit_count": [],
        "paper_role_hit_rate": [],
        "table_hit_rate": [],
        "figure_hit_rate": [],
        "numeric_qa_exact_match": [],
        "top5_cross_paper_completeness": [],
        "chunk_hit_rate": [],
        "exact_chunk_hit": [],
        "overlap_chunk_hit": [],
        "anchor_hit": [],
        "section_mrr": [],
        "single_paper_recall_at_5": [],
        "cross_paper_recall_at_5": [],
        "hard_query_hit_rate": [],
        "latency_ms": [],
    }

    query_details: List[Dict[str, Any]] = []
    failure_buckets = {
        "retrieval_miss": 0,
        "paper_hit_but_section_miss": 0,
        "section_hit_but_chunk_miss": 0,
        "evaluation_mapping_error": 0,
    }

    async def evaluate_case(query_data: Dict[str, Any], paper_ids: List[str], default_type: str) -> None:
        started_at = time.perf_counter()
        result = await _run_single_query(
            service,
            query_data,
            user_id=user_id,
            paper_ids=paper_ids,
            use_reranker=use_reranker,
            mock_mode=mock_mode,
        )
        latency_ms = (time.perf_counter() - started_at) * 1000.0

        results = result.get("results", [])
        expected_chunks = query_data.get("expected_chunks") or []
        expected_papers = query_data.get("expected_paper_ids") or query_data.get("paper_ids") or paper_ids

        if expected_chunks:
            retrieved_ids = [
                str(item.get("source_id") or item.get("id") or item.get("chunk_id") or "")
                for item in results
            ]
            expected_ids = expected_chunks
        else:
            retrieved_ids = [str(item.get("paper_id") or "") for item in results]
            expected_ids = expected_papers

        expected_sections = query_data.get("expected_sections") or []
        query_family = result.get("query_family") or query_data.get("query_family") or query_data.get("query_type") or default_type
        query_type = str(query_data.get("query_type") or query_family)

        recall_5 = calculate_recall_at_k(retrieved_ids, expected_ids, 5)
        recall_10 = calculate_recall_at_k(retrieved_ids, expected_ids, 10)
        mrr = calculate_mrr(retrieved_ids, expected_ids)
        section_hit = calculate_section_hit_rate(results, expected_sections)
        paper_hit = calculate_paper_hit_rate(results, expected_papers)
        cross_paper_top5 = calculate_top5_cross_paper_completeness(results, expected_papers)
        table_hit = calculate_table_hit_rate(results, query_data.get("gold_table_refs") or [])
        figure_hit = calculate_figure_hit_rate(results, query_data.get("gold_figure_refs") or [])
        numeric_exact = calculate_numeric_qa_exact_match(results, query_data.get("gold_metric_triplets") or [])
        expected_chunks = query_data.get("expected_chunk_ids") or query_data.get("expected_chunks") or []
        chunk_metrics = calculate_chunk_match_metrics(results, expected_chunks)
        chunk_hit = chunk_metrics["chunk_hit_rate"]
        section_mrr = calculate_section_mrr(results, expected_sections)
        failure_bucket = classify_failure_bucket(
            results=results,
            expected_paper_ids=expected_papers,
            expected_sections=expected_sections,
            chunk_metrics=chunk_metrics,
            expected_chunks=expected_chunks,
        )
        if failure_bucket:
            failure_buckets[failure_bucket] += 1

        evidence_bundle_hit_count = len(
            {
                str(item.get("evidence_bundle_id"))
                for item in results[:10]
                if item.get("evidence_bundle_id")
            }
        )
        paper_role_hits = sum(1 for item in results[:10] if item.get("paper_role"))
        paper_role_hit_rate = (paper_role_hits / min(len(results), 10)) if results else 0.0

        metrics["recall_at_5"].append(recall_5)
        metrics["recall_at_10"].append(recall_10)
        metrics["mrr"].append(mrr)
        metrics["section_hit_rate"].append(section_hit)
        metrics["paper_hit_rate"].append(paper_hit)
        metrics["planner_query_count"].append(float(result.get("planner_query_count") or 0.0))
        metrics["second_pass_used"].append(1.0 if result.get("second_pass_used") else 0.0)
        metrics["second_pass_gain"].append(float(result.get("second_pass_gain") or 0.0))
        metrics["evidence_bundle_hit_count"].append(float(evidence_bundle_hit_count))
        metrics["paper_role_hit_rate"].append(paper_role_hit_rate)
        metrics["table_hit_rate"].append(table_hit)
        metrics["figure_hit_rate"].append(figure_hit)
        metrics["numeric_qa_exact_match"].append(numeric_exact)
        metrics["top5_cross_paper_completeness"].append(cross_paper_top5)
        metrics["chunk_hit_rate"].append(chunk_hit)
        metrics["exact_chunk_hit"].append(chunk_metrics["exact_chunk_hit"])
        metrics["overlap_chunk_hit"].append(chunk_metrics["overlap_chunk_hit"])
        metrics["anchor_hit"].append(chunk_metrics["anchor_hit"])
        metrics["section_mrr"].append(section_mrr)
        metrics["latency_ms"].append(latency_ms)
        if query_type.startswith("single"):
            metrics["single_paper_recall_at_5"].append(recall_5)
        if query_type in {"cross_paper", "compare"}:
            metrics["cross_paper_recall_at_5"].append(recall_5)
        if query_type == "hard":
            metrics["hard_query_hit_rate"].append(1.0 if paper_hit >= 1.0 else 0.0)

        query_details.append(
            {
                "query_id": query_data.get("id"),
                "query_family": query_family,
                "planner_query_count": int(result.get("planner_query_count") or 0),
                "decontextualized_query": result.get("decontextualized_query"),
                "second_pass_used": bool(result.get("second_pass_used")),
                "second_pass_gain": float(result.get("second_pass_gain") or 0.0),
                "evidence_bundle_hit_count": evidence_bundle_hit_count,
                "paper_role_hit_rate": paper_role_hit_rate,
                "table_hit_rate": table_hit,
                "figure_hit_rate": figure_hit,
                "numeric_qa_exact_match": numeric_exact,
                "top5_cross_paper_completeness": cross_paper_top5,
                "recall_at_5": recall_5,
                "recall_at_10": recall_10,
                "mrr": mrr,
                "paper_hit_rate": paper_hit,
                "section_hit_rate": section_hit,
                "chunk_hit_rate": chunk_hit,
                "exact_chunk_hit": chunk_metrics["exact_chunk_hit"],
                "overlap_chunk_hit": chunk_metrics["overlap_chunk_hit"],
                "anchor_hit": chunk_metrics["anchor_hit"],
                "section_mrr": section_mrr,
                "latency_ms": latency_ms,
                "query_type": query_type,
                "failure_bucket": failure_bucket,
            }
        )

    for paper_data in golden.get("papers", []):
        paper_id = paper_data.get("paper_id")
        if paper_ids_filter and paper_id not in paper_ids_filter:
            continue
        for query_data in paper_data.get("queries", []):
            await evaluate_case(query_data, [paper_id], "fact")

    for cp in golden.get("cross_paper_queries", []):
        target_papers = cp.get("paper_ids", [])
        if paper_ids_filter:
            target_papers = [pid for pid in target_papers if pid in paper_ids_filter]
        await evaluate_case(cp, target_papers, "compare")

    for mq in golden.get("multimodal_queries", []):
        result = await _run_single_query(
            service,
            mq,
            user_id=user_id,
            paper_ids=paper_ids_filter or mq.get("paper_ids", []),
            use_reranker=use_reranker,
            mock_mode=mock_mode,
        )
        results = result.get("results", [])
        expected_types = mq.get("expected_content_type", [])
        retrieved_types = [str(item.get("content_type")) for item in results[:10]]
        hit = any(item in retrieved_types for item in expected_types) if expected_types else False
        metrics["multimodal_hit_rate"].append(1.0 if hit else 0.0)
        query_details.append(
            {
                "query_id": mq.get("id"),
                "query_family": result.get("query_family") or mq.get("query_family") or "multimodal",
                "multimodal_hit": hit,
                "expected_types": expected_types,
                "planner_query_count": int(result.get("planner_query_count") or 0),
                "decontextualized_query": result.get("decontextualized_query"),
                "second_pass_used": bool(result.get("second_pass_used")),
                "second_pass_gain": float(result.get("second_pass_gain") or 0.0),
                "evidence_bundle_hit_count": len(
                    {
                        str(item.get("evidence_bundle_id"))
                        for item in results[:10]
                        if item.get("evidence_bundle_id")
                    }
                ),
            }
        )

    report = {
        "total_queries": len(metrics["recall_at_5"]),
        "recall_at_5_avg": _avg(metrics["recall_at_5"]),
        "recall_at_10_avg": _avg(metrics["recall_at_10"]),
        "mrr_avg": _avg(metrics["mrr"]),
        "section_hit_rate_avg": _avg(metrics["section_hit_rate"]),
        "multimodal_hit_rate_avg": _avg(metrics["multimodal_hit_rate"]),
        "paper_hit_rate_avg": _avg(metrics["paper_hit_rate"]),
        "planner_query_count_avg": _avg(metrics["planner_query_count"]),
        "second_pass_used_rate": _avg(metrics["second_pass_used"]),
        "second_pass_gain_avg": _avg(metrics["second_pass_gain"]),
        "evidence_bundle_hit_count_avg": _avg(metrics["evidence_bundle_hit_count"]),
        "paper_role_hit_rate_avg": _avg(metrics["paper_role_hit_rate"]),
        "table_hit_rate_avg": _avg(metrics["table_hit_rate"]),
        "figure_hit_rate_avg": _avg(metrics["figure_hit_rate"]),
        "numeric_qa_exact_match": _avg(metrics["numeric_qa_exact_match"]),
        "top5_cross_paper_completeness": _avg(metrics["top5_cross_paper_completeness"]),
        "chunk_hit_rate_avg": _avg(metrics["chunk_hit_rate"]),
        "exact_chunk_hit_avg": _avg(metrics["exact_chunk_hit"]),
        "overlap_chunk_hit_avg": _avg(metrics["overlap_chunk_hit"]),
        "anchor_hit_avg": _avg(metrics["anchor_hit"]),
        "section_mrr_avg": _avg(metrics["section_mrr"]),
        "single_paper_recall_at_5": _avg(metrics["single_paper_recall_at_5"]),
        "cross_paper_recall_at_5": _avg(metrics["cross_paper_recall_at_5"]),
        "hard_query_hit_rate": _avg(metrics["hard_query_hit_rate"]),
        "latency_avg_ms": _avg(metrics["latency_ms"]),
        "latency_p95_ms": _p95(metrics["latency_ms"]),
        "metrics_raw": metrics,
        "failure_buckets": failure_buckets,
        "query_details": query_details,
        "evaluation_mode": "mock" if mock_mode else "real",
        "use_reranker": bool(use_reranker),
        "dataset_label": dataset_label,
        "model_stack": model_stack,
        "run_label": run_label,
        "experiment_tag": f"{dataset_label}_{model_stack}_{'on' if use_reranker else 'off'}_{run_label}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return report


def _markdown_summary_table(report: Dict[str, Any]) -> str:
    return "\n".join(
        [
            "| dataset | model_stack | reranker | run | recall@5 | recall@10 | mrr | paper_hit | section_hit | chunk_hit | cross_paper_r@5 | hard_hit | avg_latency_ms | p95_latency_ms |",
            "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
            (
                f"| {report['dataset_label']} | {report['model_stack']} | {'on' if report['use_reranker'] else 'off'} "
                f"| {report['run_label']} | {report['recall_at_5_avg']:.4f} | {report['recall_at_10_avg']:.4f} "
                f"| {report['mrr_avg']:.4f} | {report['paper_hit_rate_avg']:.4f} | {report['section_hit_rate_avg']:.4f} "
                f"| {report['chunk_hit_rate_avg']:.4f} | {report['cross_paper_recall_at_5']:.4f} | {report['hard_query_hit_rate']:.4f} "
                f"| {report['latency_avg_ms']:.2f} | {report['latency_p95_ms']:.2f} |"
            ),
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Retrieval evaluation harness")
    parser.add_argument("--golden", default="tests/evals/golden_queries.json", help="Path to golden queries JSON")
    parser.add_argument("--paper-id", nargs="*", help="Filter by specific paper IDs")
    parser.add_argument("--user-id", default="eval-user", help="User id to query against")
    parser.add_argument("--output", default="eval_retrieval_report.json", help="Output report path")
    parser.add_argument("--allow-mock", action="store_true", help="Run in mock mode")
    parser.add_argument("--use-reranker", action="store_true", help="Enable reranker during evaluation")
    parser.add_argument("--dataset-label", default="unknown", help="Dataset label, e.g., large/xlarge")
    parser.add_argument("--model-stack", default="manual", help="Model stack label, e.g., bge_dual/qwen_dual")
    parser.add_argument("--run-label", default="round1", help="Run label, e.g., round1/round2")
    parser.add_argument("--markdown-summary", default="", help="Optional markdown summary output path")
    args = parser.parse_args()

    report = asyncio.run(
        evaluate_retrieval(
            args.golden,
            user_id=args.user_id,
            paper_ids_filter=args.paper_id,
            mock_mode=args.allow_mock,
            use_reranker=args.use_reranker,
            dataset_label=args.dataset_label,
            model_stack=args.model_stack,
            run_label=args.run_label,
        )
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.markdown_summary:
        markdown_path = Path(args.markdown_summary)
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(_markdown_summary_table(report), encoding="utf-8")

    print("=" * 60)
    print("Retrieval Evaluation Report")
    print("=" * 60)
    print(f"Total Queries: {report['total_queries']}")
    print(f"Recall@5: {report['recall_at_5_avg']:.2%}")
    print(f"MRR: {report['mrr_avg']:.2%}")
    print(f"Paper Hit Rate: {report['paper_hit_rate_avg']:.2%}")
    print(f"Table Hit Rate: {report['table_hit_rate_avg']:.2%}")
    print(f"Figure Hit Rate: {report['figure_hit_rate_avg']:.2%}")
    print(f"Numeric QA EM: {report['numeric_qa_exact_match']:.2%}")
    print(f"Top5 Cross-paper Completeness: {report['top5_cross_paper_completeness']:.2%}")
    print(f"Chunk Hit Rate: {report['chunk_hit_rate_avg']:.2%}")
    print(f"Exact Chunk Hit: {report['exact_chunk_hit_avg']:.2%}")
    print(f"Overlap Chunk Hit: {report['overlap_chunk_hit_avg']:.2%}")
    print(f"Anchor Hit: {report['anchor_hit_avg']:.2%}")
    print(f"Section MRR: {report['section_mrr_avg']:.2%}")
    print(f"Single-paper Recall@5: {report['single_paper_recall_at_5']:.2%}")
    print(f"Cross-paper Recall@5: {report['cross_paper_recall_at_5']:.2%}")
    print(f"Hard Query Hit Rate: {report['hard_query_hit_rate']:.2%}")
    print(f"Latency Avg/P95(ms): {report['latency_avg_ms']:.2f}/{report['latency_p95_ms']:.2f}")
    print("=" * 60)
    print(f"Report saved to: {output_path}")


if __name__ == "__main__":
    main()
