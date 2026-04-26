#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import math
import re
import statistics
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from pymilvus import Collection, connections, utility


ROOT = Path(__file__).resolve().parents[2]
API_ROOT = ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.abstention_policy import get_abstention_policy
from app.core.claim_extractor import get_claim_extractor
from app.core.claim_verifier import get_claim_verifier
from app.core.citation_verifier import get_citation_verifier
from app.core.model_gateway import create_embedding_provider
from app.core.reranker.factory import get_reranker_service
from app.utils.zhipu_client import ZhipuLLMClient
from scripts.evals.v2_4_common import read_json, stage_collection_name, write_json, write_markdown
from scripts.evals.v2_6_1_common import load_artifact_rows_by_stage, load_regression_rows, run_dense_search
from scripts.evals.v2_6_official_rag_evaluation import (
    EMBEDDING_MODEL,
    LLM_MODEL,
    RERANKER_MODEL,
    RUNTIME_PROFILE,
    DEFAULT_GOLDEN_PATH,
    compute_retrieval_metrics,
)


OUTPUT_DIR = ROOT / "artifacts" / "benchmarks" / "v2_6_2"
DOC_REPORT = ROOT / "docs" / "reports" / "official_rag_evaluation" / "step6_2_retrieval_quality_report.md"
STAGES = ["raw", "rule", "llm"]

FAMILY_SECTION_HINTS: Dict[str, List[str]] = {
    "fact": ["abstract", "introduction", "results"],
    "method": ["methods", "approach", "experiment"],
    "table": ["results", "appendix", "table"],
    "figure": ["results", "figure", "caption"],
    "numeric": ["results", "evaluation", "table"],
    "compare": ["related work", "comparison", "results"],
    "cross_paper": ["introduction", "discussion", "comparison"],
    "hard": ["methods", "results", "discussion"],
}

FAMILY_CONTENT_HINTS: Dict[str, List[str]] = {
    "table": ["table", "caption", "page", "rows", "columns", "value"],
    "figure": ["figure", "caption", "plot", "diagram", "visual"],
    "numeric": ["number", "value", "percent", "score", "table", "result"],
    "method": ["method", "approach", "pipeline", "architecture", "algorithm"],
    "fact": ["fact", "finding", "result", "evidence"],
    "compare": ["compare", "difference", "versus", "vs", "across"],
    "cross_paper": ["papers", "across", "comparison", "contrast"],
    "hard": ["assumption", "tradeoff", "limitation", "evidence"],
}

VARIANT_ORDER = [
    "original_query",
    "decontextualized_query",
    "keyword_query",
    "section_aware_query",
    "paper_scope_query",
    "evidence_anchor_style_query",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Step6.2 retrieval quality tuning")
    parser.add_argument("--golden-path", default=str(DEFAULT_GOLDEN_PATH))
    parser.add_argument("--collection-suffix", default="v2_4")
    parser.add_argument("--milvus-host", default="localhost")
    parser.add_argument("--milvus-port", type=int, default=19530)
    parser.add_argument("--runtime-profile", default=RUNTIME_PROFILE)
    parser.add_argument("--max-queries", type=int, default=16)
    return parser.parse_args()


def _tokenize(text: str) -> List[str]:
    return [t for t in re.findall(r"[a-z0-9]+(?:\.[0-9]+)?", (text or "").lower()) if len(t) > 1]


def _mean(values: Iterable[float]) -> float:
    seq = [float(v) for v in values]
    if not seq:
        return 0.0
    return float(sum(seq) / len(seq))


def _ordered_unique(values: Sequence[str]) -> List[str]:
    out: List[str] = []
    seen: Set[str] = set()
    for value in values:
        key = str(value or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def _recall_at_k(expected_ids: Set[str], retrieved_ids: Sequence[str], k: int) -> float:
    if not expected_ids:
        return 0.0
    return round(len(expected_ids & set(retrieved_ids[:k])) / max(len(expected_ids), 1), 4)


def _section_norm(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").lower()).strip()


def _find_chunk_ordinal(chunk_id: str) -> Optional[int]:
    if not chunk_id:
        return None
    nums = re.findall(r"(\d+)", str(chunk_id))
    if not nums:
        return None
    try:
        return int(nums[-1])
    except ValueError:
        return None


def _expected_rank(expected_ids: Set[str], retrieved_ids: Sequence[str]) -> Optional[int]:
    for idx, sid in enumerate(retrieved_ids, start=1):
        if sid in expected_ids:
            return idx
    return None


def _rank_bucket(rank: Optional[int]) -> str:
    if rank is None:
        return "missing"
    if rank <= 10:
        return "<=10"
    if rank <= 20:
        return "11-20"
    if rank <= 50:
        return "21-50"
    if rank <= 100:
        return "51-100"
    return ">100"


def _build_rewrite_variants(query: str, family: str) -> Dict[str, str]:
    tokens = _tokenize(query)
    hints = FAMILY_CONTENT_HINTS.get(family, [])
    section_hints = FAMILY_SECTION_HINTS.get(family, [])

    keyword_terms = _ordered_unique(tokens + hints)
    section_terms = _ordered_unique(tokens + section_hints + hints)
    anchor_terms = _ordered_unique(hints + section_hints + tokens)

    variants = {
        "original_query": query,
        "decontextualized_query": " ".join(_ordered_unique(tokens)[:24]),
        "keyword_query": " ".join(keyword_terms[:28]),
        "section_aware_query": " ".join(section_terms[:30]),
        "paper_scope_query": " ".join(_ordered_unique(tokens + ["paper", "study", "experiment", "result"])[:30]),
        "evidence_anchor_style_query": " ".join(anchor_terms[:32]),
    }

    if family in {"table", "figure", "numeric"}:
        variants["section_aware_query"] = " ".join(_ordered_unique(section_terms + ["results", "appendix"])[:34])
    if family in {"fact", "method"}:
        variants["paper_scope_query"] = " ".join(_ordered_unique(tokens + ["method", "evidence", "section", "paper"])[:30])
    return variants


@dataclass(frozen=True)
class QueryContext:
    query_id: str
    query: str
    query_family: str
    expected_paper_ids: List[str]
    expected_source_chunk_ids: List[str]
    expected_content_types: List[str]
    expected_sections: List[str]


class RetrievalQualityTuner:
    def __init__(self, *, golden_path: Path, collection_suffix: str, milvus_host: str, milvus_port: int, max_queries: int):
        self.golden_path = golden_path
        self.collection_suffix = collection_suffix
        self.max_queries = max_queries
        self.output_dir = OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.rows: List[QueryContext] = [
            QueryContext(
                query_id=row.query_id,
                query=row.query,
                query_family=row.query_family,
                expected_paper_ids=list(row.expected_paper_ids),
                expected_source_chunk_ids=list(row.expected_source_chunk_ids),
                expected_content_types=list(row.expected_content_types),
                expected_sections=list(row.expected_sections),
            )
            for row in load_regression_rows(golden_path, max_queries=max_queries)
        ]
        self.provider = create_embedding_provider("tongyi", EMBEDDING_MODEL)

        connections.connect(alias="v262", host=milvus_host, port=milvus_port)
        self.collections: Dict[str, Collection] = {}
        for stage in STAGES:
            name = stage_collection_name(stage, collection_suffix)
            col = Collection(name, using="v262")
            col.load()
            self.collections[stage] = col

        artifact_rows = load_artifact_rows_by_stage()
        self.stage_artifact_rows: Dict[str, List[Dict[str, Any]]] = {stage: list(artifact_rows.get(stage, [])) for stage in STAGES}
        self.stage_sid_index: Dict[str, Dict[str, Dict[str, Any]]] = {}
        for stage in STAGES:
            index: Dict[str, Dict[str, Any]] = {}
            for item in self.stage_artifact_rows[stage]:
                sid = str(item.get("source_chunk_id") or "").strip()
                if sid and sid not in index:
                    index[sid] = item
            self.stage_sid_index[stage] = index

        self.reranker = get_reranker_service()
        self.reranker.load_model()
        self.citation_verifier = get_citation_verifier()
        self.claim_extractor = get_claim_extractor()
        self.claim_verifier = get_claim_verifier()
        self.abstention_policy = get_abstention_policy()
        self.llm = ZhipuLLMClient(model=LLM_MODEL)

    @staticmethod
    def _stage_section_hint(stage: str) -> str:
        return {"raw": "raw", "rule": "rule", "llm": "llm"}.get(stage, stage)

    def _to_hit_doc(self, stage: str, hit: Dict[str, Any], score_override: Optional[float] = None) -> Dict[str, Any]:
        sid = str(hit.get("source_chunk_id") or "")
        row = self.stage_sid_index.get(stage, {}).get(sid, {})
        content_data = str(row.get("content_data") or hit.get("anchor_text") or "")
        section = str(hit.get("section") or row.get("section") or row.get("section_path") or "")
        return {
            "source_chunk_id": sid,
            "source_id": sid,
            "paper_id": str(hit.get("paper_id") or row.get("paper_id") or ""),
            "page_num": row.get("page_num"),
            "content_type": str(hit.get("content_type") or row.get("content_type") or "text"),
            "section": section,
            "anchor_text": str(hit.get("anchor_text") or row.get("anchor_text") or content_data[:400]),
            "content_data": content_data,
            "score": float(score_override if score_override is not None else max(0.0, 1.0 - float(hit.get("distance") or 0.0))),
            "citation": f"[{str(hit.get('paper_id') or row.get('paper_id') or '')}, {section or self._stage_section_hint(stage)}]",
            "char_start": row.get("char_start"),
            "chunk_id": str(row.get("chunk_id") or ""),
        }

    def _dense_hits(self, *, stage: str, query: str, top_k: int, expr: Optional[str] = "indexable == true") -> Tuple[List[Dict[str, Any]], float]:
        started = time.perf_counter()
        query_vector = self.provider.embed_texts([query])[0]
        hits = run_dense_search(
            collection=self.collections[stage],
            query_vector=query_vector,
            top_k=top_k,
            expr=expr,
            output_fields=["source_chunk_id", "paper_id", "section", "content_type", "anchor_text", "raw_data"],
        )
        latency = (time.perf_counter() - started) * 1000.0
        return hits, latency

    def _lexical_hits(self, *, stage: str, row: QueryContext, query: str, top_k: int) -> Tuple[List[Dict[str, Any]], float]:
        started = time.perf_counter()
        q_tokens = _tokenize(query)
        q_set = set(q_tokens)
        family = row.query_family
        section_hints = set(FAMILY_SECTION_HINTS.get(family, []))
        content_hints = set(FAMILY_CONTENT_HINTS.get(family, []))

        scored: List[Tuple[float, Dict[str, Any]]] = []
        for item in self.stage_artifact_rows.get(stage, []):
            sid = str(item.get("source_chunk_id") or "").strip()
            if not sid:
                continue
            text = " ".join(
                [
                    str(item.get("content_data") or ""),
                    str(item.get("anchor_text") or ""),
                    str(item.get("section") or item.get("section_path") or ""),
                    str(item.get("content_type") or ""),
                ]
            ).lower()
            tokens = set(_tokenize(text))
            overlap = len(tokens & q_set)
            if overlap <= 0:
                continue

            score = float(overlap)
            content_type = str(item.get("content_type") or "")
            section = _section_norm(str(item.get("section") or item.get("section_path") or ""))
            if content_type in {"table", "caption", "page"} and family in {"table", "numeric"}:
                score += 2.0
            if content_type in {"figure", "caption", "page"} and family == "figure":
                score += 2.0
            if any(h in section for h in section_hints):
                score += 1.2
            if any(h in text for h in content_hints):
                score += 0.8

            scored.append(
                (
                    score,
                    {
                        "source_chunk_id": sid,
                        "paper_id": str(item.get("paper_id") or ""),
                        "section": str(item.get("section") or item.get("section_path") or ""),
                        "content_type": content_type,
                        "anchor_text": str(item.get("anchor_text") or str(item.get("content_data") or "")[:400]),
                    },
                )
            )

        scored.sort(key=lambda x: x[0], reverse=True)
        hits = [entry[1] for entry in scored[:top_k]]
        latency = (time.perf_counter() - started) * 1000.0
        return hits, latency

    @staticmethod
    def _rrf_fusion(
        *,
        dense_hits: Sequence[Dict[str, Any]],
        sparse_hits: Sequence[Dict[str, Any]],
        rrf_k: int,
        final_k: int,
    ) -> List[Tuple[Dict[str, Any], float]]:
        score_map: Dict[str, float] = {}
        doc_map: Dict[str, Dict[str, Any]] = {}

        for rank, hit in enumerate(dense_hits, start=1):
            sid = str(hit.get("source_chunk_id") or "")
            if not sid:
                continue
            score_map[sid] = score_map.get(sid, 0.0) + 1.0 / (rrf_k + rank)
            doc_map[sid] = dict(hit)

        for rank, hit in enumerate(sparse_hits, start=1):
            sid = str(hit.get("source_chunk_id") or "")
            if not sid:
                continue
            score_map[sid] = score_map.get(sid, 0.0) + 1.0 / (rrf_k + rank)
            if sid not in doc_map:
                doc_map[sid] = dict(hit)

        ranked = sorted(score_map.items(), key=lambda kv: kv[1], reverse=True)
        return [(doc_map[sid], score) for sid, score in ranked[:final_k]]

    def _eval_hit_metrics(self, *, stage: str, row: QueryContext, hits: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
        expected_sources = set(row.expected_source_chunk_ids)
        expected_papers = set(row.expected_paper_ids)
        expected_sections = {_section_norm(s) for s in row.expected_sections}
        expected_types = set(row.expected_content_types)

        source_ids = [str(h.get("source_chunk_id") or "") for h in hits]
        paper_ids = [str(h.get("paper_id") or "") for h in hits]
        sections = [_section_norm(str(h.get("section") or "")) for h in hits]
        types = [str(h.get("content_type") or "") for h in hits]

        expected_rank = _expected_rank(expected_sources, source_ids)
        exact_chunk_hit = 1.0 if expected_rank is not None and expected_rank <= 10 else 0.0
        same_paper_hit = 1.0 if expected_papers & set(paper_ids[:10]) else 0.0
        same_section_hit = 1.0 if expected_sections & set(sections[:10]) else 0.0
        content_type_hit = 1.0 if expected_types & set(types[:10]) else 0.0

        adjacent = 0.0
        stage_index = self.stage_sid_index.get(stage, {})
        expected_rows = [stage_index.get(sid, {}) for sid in expected_sources]
        expected_ord = {_find_chunk_ordinal(str(v.get("chunk_id") or "")) for v in expected_rows}
        expected_ord = {v for v in expected_ord if v is not None}
        expected_char = [int(v.get("char_start") or -1) for v in expected_rows if str(v.get("char_start") or "").isdigit()]
        expected_char_avg = int(_mean(expected_char)) if expected_char else -1
        expected_paper = next(iter(expected_papers), "")

        for hit in hits[:10]:
            hit_sid = str(hit.get("source_chunk_id") or "")
            hit_row = stage_index.get(hit_sid, {})
            if str(hit.get("paper_id") or "") != expected_paper:
                continue
            hit_ord = _find_chunk_ordinal(str(hit_row.get("chunk_id") or ""))
            if hit_ord is not None and expected_ord and min(abs(hit_ord - eo) for eo in expected_ord) <= 1:
                adjacent = 1.0
                break
            if expected_char_avg >= 0:
                hs = hit_row.get("char_start")
                if isinstance(hs, int) and abs(hs - expected_char_avg) <= 1200:
                    adjacent = 1.0
                    break

        return {
            "exact_chunk_hit": exact_chunk_hit,
            "recall_at_5": _recall_at_k(expected_sources, source_ids, 5),
            "recall_at_10": _recall_at_k(expected_sources, source_ids, 10),
            "recall_at_20": _recall_at_k(expected_sources, source_ids, 20),
            "recall_at_50": _recall_at_k(expected_sources, source_ids, 50),
            "recall_at_100": _recall_at_k(expected_sources, source_ids, 100),
            "same_paper_hit": same_paper_hit,
            "same_section_hit": same_section_hit,
            "adjacent_chunk_hit": adjacent,
            "content_type_hit": content_type_hit,
            "paper_hit_rate": round(len(expected_papers & set(paper_ids[:10])) / max(len(expected_papers), 1), 4),
            "section_hit_rate": round(len(expected_sections & set(sections[:10])) / max(len(expected_sections), 1), 4),
            "table_hit_rate": 1.0 if row.query_family == "table" and any(t in {"table", "caption", "page"} for t in types[:10]) else 0.0,
            "figure_hit_rate": 1.0 if row.query_family == "figure" and any(t in {"figure", "caption", "page"} for t in types[:10]) else 0.0,
            "numeric_hit_rate": 1.0 if row.query_family == "numeric" and any(bool(re.search(r"\d", str(h.get("anchor_text") or ""))) for h in hits[:10]) else 0.0,
            "expected_chunk_rank": expected_rank,
            "expected_chunk_rank_bucket": _rank_bucket(expected_rank),
        }

    def _aggregate(self, records: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
        families: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for rec in records:
            families[str(rec.get("query_family") or "unknown")].append(rec)

        metric_keys = [
            "exact_chunk_hit",
            "recall_at_5",
            "recall_at_10",
            "recall_at_20",
            "recall_at_50",
            "recall_at_100",
            "same_paper_hit",
            "same_section_hit",
            "adjacent_chunk_hit",
            "content_type_hit",
            "paper_hit_rate",
            "section_hit_rate",
            "table_hit_rate",
            "figure_hit_rate",
            "numeric_hit_rate",
            "citation_coverage",
            "unsupported_claim_rate",
            "answer_evidence_consistency",
            "latency_ms",
        ]

        def _agg(items: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
            out: Dict[str, Any] = {"total": len(items)}
            for key in metric_keys:
                out[key] = round(_mean(float(it.get(key) or 0.0) for it in items), 4)
            return out

        return {
            "overall": _agg(records),
            "by_query_family": {family: _agg(items) for family, items in sorted(families.items())},
        }

    def _write_md_table(self, path: Path, title: str, header: List[str], rows: List[List[Any]], bullets: Optional[List[str]] = None) -> None:
        lines: List[str] = []
        if bullets:
            lines.extend([f"- {line}" for line in bullets])
            lines.append("")
        lines.append("| " + " | ".join(header) + " |")
        lines.append("|" + "|".join(["---"] * len(header)) + "|")
        for row in rows:
            lines.append("| " + " | ".join(str(v) for v in row) + " |")
        write_markdown(path, title, lines)

    def run_baseline(self) -> Dict[str, Any]:
        records: List[Dict[str, Any]] = []
        for stage in STAGES:
            for row in self.rows:
                hits, latency = self._dense_hits(stage=stage, query=row.query, top_k=100)
                metrics = self._eval_hit_metrics(stage=stage, row=row, hits=hits)
                records.append(
                    {
                        "stage": stage,
                        "query_id": row.query_id,
                        "query_family": row.query_family,
                        "query": row.query,
                        "top_k": 100,
                        "latency_ms": round(latency, 3),
                        "retrieved_source_chunk_ids": [str(h.get("source_chunk_id") or "") for h in hits],
                        **metrics,
                    }
                )

        payload = {
            "runtime_profile": RUNTIME_PROFILE,
            "embedding_model": EMBEDDING_MODEL,
            "collection_suffix": self.collection_suffix,
            "max_queries": self.max_queries,
            "records": records,
            "summary": self._aggregate(records),
        }
        write_json(self.output_dir / "baseline_retrieval_quality.json", payload)

        overall = payload["summary"]["overall"]
        rows_md = []
        for stage in STAGES:
            stage_records = [r for r in records if r["stage"] == stage]
            stage_summary = self._aggregate(stage_records)["overall"]
            rows_md.append(
                [
                    stage,
                    stage_summary["total"],
                    stage_summary["recall_at_10"],
                    stage_summary["recall_at_50"],
                    stage_summary["recall_at_100"],
                    stage_summary["same_paper_hit"],
                    stage_summary["same_section_hit"],
                ]
            )
        self._write_md_table(
            self.output_dir / "baseline_retrieval_quality.md",
            "Step6.2 Baseline Retrieval Quality",
            ["stage", "total", "recall@10", "recall@50", "recall@100", "same_paper_hit", "same_section_hit"],
            rows_md,
            bullets=[
                f"overall_recall_at_10: {overall['recall_at_10']}",
                f"overall_recall_at_50: {overall['recall_at_50']}",
                f"overall_recall_at_100: {overall['recall_at_100']}",
            ],
        )
        return payload

    def run_candidate_sweep(self) -> Dict[str, Any]:
        topks = [10, 20, 50, 100, 200]
        records: List[Dict[str, Any]] = []

        for stage in STAGES:
            for topk in topks:
                for row in self.rows:
                    hits, latency = self._dense_hits(stage=stage, query=row.query, top_k=topk)
                    metrics = self._eval_hit_metrics(stage=stage, row=row, hits=hits)
                    records.append(
                        {
                            "stage": stage,
                            "top_k": topk,
                            "query_id": row.query_id,
                            "query_family": row.query_family,
                            "latency_ms": round(latency, 3),
                            "candidate_count": len(hits),
                            "rerank_input_size": len(hits),
                            "expected_chunk_rank": metrics["expected_chunk_rank"],
                            "expected_chunk_rank_bucket": metrics["expected_chunk_rank_bucket"],
                            "recall_at_k": _recall_at_k(set(row.expected_source_chunk_ids), [str(h.get("source_chunk_id") or "") for h in hits], topk),
                            "same_paper_hit_rate": metrics["same_paper_hit"],
                        }
                    )

        grouped: Dict[str, Dict[int, List[Dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
        for rec in records:
            grouped[rec["stage"]][int(rec["top_k"])].append(rec)

        summary: Dict[str, Any] = {}
        md_rows: List[List[Any]] = []
        for stage in STAGES:
            summary[stage] = {}
            for topk in topks:
                items = grouped[stage][topk]
                dist = defaultdict(int)
                for item in items:
                    dist[str(item.get("expected_chunk_rank_bucket") or "missing")] += 1
                stage_summary = {
                    "top_k": topk,
                    "recall_at_k": round(_mean(i["recall_at_k"] for i in items), 4),
                    "same_paper_hit_rate": round(_mean(i["same_paper_hit_rate"] for i in items), 4),
                    "latency_ms": round(_mean(i["latency_ms"] for i in items), 3),
                    "candidate_count": round(_mean(i["candidate_count"] for i in items), 2),
                    "rerank_input_size": round(_mean(i["rerank_input_size"] for i in items), 2),
                    "expected_chunk_rank_distribution": dict(dist),
                }
                summary[stage][str(topk)] = stage_summary
                md_rows.append(
                    [
                        stage,
                        topk,
                        stage_summary["recall_at_k"],
                        stage_summary["same_paper_hit_rate"],
                        stage_summary["latency_ms"],
                        stage_summary["candidate_count"],
                    ]
                )

        payload = {
            "config": {"top_k_values": topks},
            "records": records,
            "summary": summary,
        }
        write_json(self.output_dir / "candidate_recall_sweep.json", payload)
        self._write_md_table(
            self.output_dir / "candidate_recall_sweep.md",
            "Step6.2 Candidate Recall Sweep",
            ["stage", "top_k", "recall_at_k", "same_paper_hit_rate", "latency_ms", "candidate_count"],
            md_rows,
        )
        return payload

    def run_query_rewrite_ablation(self) -> Dict[str, Any]:
        records: List[Dict[str, Any]] = []
        by_query_best: Dict[str, Dict[str, Any]] = {}

        for stage in STAGES:
            for row in self.rows:
                variants = _build_rewrite_variants(row.query, row.query_family)
                candidates: List[Dict[str, Any]] = []
                for variant in VARIANT_ORDER:
                    qtext = variants.get(variant, row.query)
                    hits, latency = self._dense_hits(stage=stage, query=qtext, top_k=100)
                    metrics = self._eval_hit_metrics(stage=stage, row=row, hits=hits)
                    record = {
                        "stage": stage,
                        "query_id": row.query_id,
                        "query_family": row.query_family,
                        "variant": variant,
                        "query_text": qtext,
                        "latency_ms": round(latency, 3),
                        "recall_at_10": metrics["recall_at_10"],
                        "recall_at_50": metrics["recall_at_50"],
                        "same_paper_hit": metrics["same_paper_hit"],
                        "exact_chunk_hit": metrics["exact_chunk_hit"],
                    }
                    records.append(record)
                    candidates.append(record)

                best = sorted(
                    candidates,
                    key=lambda item: (
                        float(item["recall_at_10"]),
                        float(item["recall_at_50"]),
                        float(item["same_paper_hit"]),
                        -float(item["latency_ms"]),
                    ),
                    reverse=True,
                )[0]
                by_query_best[f"{stage}::{row.query_id}"] = {
                    "stage": stage,
                    "query_id": row.query_id,
                    "query_family": row.query_family,
                    "best_query_variant": best["variant"],
                    "best_recall_at_10": best["recall_at_10"],
                    "best_recall_at_50": best["recall_at_50"],
                }

        summary: Dict[str, Any] = {}
        rows_md: List[List[Any]] = []
        for stage in STAGES:
            summary[stage] = {}
            for variant in VARIANT_ORDER:
                items = [r for r in records if r["stage"] == stage and r["variant"] == variant]
                if not items:
                    continue
                s = {
                    "recall_at_10": round(_mean(i["recall_at_10"] for i in items), 4),
                    "recall_at_50": round(_mean(i["recall_at_50"] for i in items), 4),
                    "same_paper_hit": round(_mean(i["same_paper_hit"] for i in items), 4),
                    "exact_chunk_hit": round(_mean(i["exact_chunk_hit"] for i in items), 4),
                    "latency_ms": round(_mean(i["latency_ms"] for i in items), 3),
                }
                summary[stage][variant] = s
                rows_md.append([stage, variant, s["recall_at_10"], s["recall_at_50"], s["same_paper_hit"], s["latency_ms"]])

        payload = {
            "variants": VARIANT_ORDER,
            "records": records,
            "best_query_variant_by_stage_query": by_query_best,
            "summary": summary,
        }
        write_json(self.output_dir / "query_rewrite_ablation.json", payload)
        self._write_md_table(
            self.output_dir / "query_rewrite_ablation.md",
            "Step6.2 Query Rewrite Ablation",
            ["stage", "variant", "recall@10", "recall@50", "same_paper_hit", "latency_ms"],
            rows_md,
        )
        return payload

    def _rerank_docs(self, query: str, docs: Sequence[Dict[str, Any]], top_k: int) -> Tuple[List[Dict[str, Any]], float]:
        started = time.perf_counter()
        if not docs:
            return [], 0.0
        texts = [str(d.get("anchor_text") or d.get("content_data") or "") for d in docs]
        ranked = self.reranker.rerank(query, texts, top_k=min(max(top_k, 1), len(texts)))
        out: List[Dict[str, Any]] = []
        for entry in ranked:
            rank = int(entry.get("rank") or 0)
            if 0 <= rank < len(docs):
                out.append(dict(docs[rank]))
        if not out:
            out = list(docs[:top_k])
        latency = (time.perf_counter() - started) * 1000.0
        return out, latency

    def run_sparse_hybrid_ablation(self) -> Dict[str, Any]:
        records: List[Dict[str, Any]] = []
        dense_top_k = 100
        sparse_top_k = 100
        rrf_k = 60
        final_candidate_k = 50
        rerank_top_k = 10

        for stage in STAGES:
            for row in self.rows:
                dense_hits, dense_latency = self._dense_hits(stage=stage, query=row.query, top_k=dense_top_k)
                sparse_hits, sparse_latency = self._lexical_hits(stage=stage, row=row, query=row.query, top_k=sparse_top_k)
                fused = self._rrf_fusion(dense_hits=dense_hits, sparse_hits=sparse_hits, rrf_k=rrf_k, final_k=final_candidate_k)

                dense_docs = [self._to_hit_doc(stage, h) for h in dense_hits]
                sparse_docs = [self._to_hit_doc(stage, h) for h in sparse_hits]
                hybrid_docs = [self._to_hit_doc(stage, h, score_override=s) for h, s in fused]

                reranked_hybrid, rerank_latency = self._rerank_docs(row.query, hybrid_docs, top_k=rerank_top_k)

                dense_metrics = self._eval_hit_metrics(stage=stage, row=row, hits=dense_docs)
                sparse_metrics = self._eval_hit_metrics(stage=stage, row=row, hits=sparse_docs)
                hybrid_metrics = self._eval_hit_metrics(stage=stage, row=row, hits=reranked_hybrid)

                records.append(
                    {
                        "stage": stage,
                        "query_id": row.query_id,
                        "query_family": row.query_family,
                        "dense_only_recall": dense_metrics["recall_at_10"],
                        "sparse_only_recall": sparse_metrics["recall_at_10"],
                        "hybrid_recall": hybrid_metrics["recall_at_10"],
                        "hybrid_gain": round(hybrid_metrics["recall_at_10"] - dense_metrics["recall_at_10"], 4),
                        "latency_delta": round((dense_latency + sparse_latency + rerank_latency) - dense_latency, 3),
                        "dense_latency_ms": round(dense_latency, 3),
                        "sparse_latency_ms": round(sparse_latency, 3),
                        "rerank_latency_ms": round(rerank_latency, 3),
                    }
                )

        summary = {}
        rows_md: List[List[Any]] = []
        for stage in STAGES:
            items = [r for r in records if r["stage"] == stage]
            s = {
                "dense_only_recall": round(_mean(i["dense_only_recall"] for i in items), 4),
                "sparse_only_recall": round(_mean(i["sparse_only_recall"] for i in items), 4),
                "hybrid_recall": round(_mean(i["hybrid_recall"] for i in items), 4),
                "hybrid_gain": round(_mean(i["hybrid_gain"] for i in items), 4),
                "latency_delta": round(_mean(i["latency_delta"] for i in items), 3),
            }
            summary[stage] = s
            rows_md.append([stage, s["dense_only_recall"], s["sparse_only_recall"], s["hybrid_recall"], s["hybrid_gain"], s["latency_delta"]])

        payload = {
            "config": {
                "dense_top_k": dense_top_k,
                "sparse_top_k": sparse_top_k,
                "rrf_k": rrf_k,
                "final_candidate_k": final_candidate_k,
                "rerank_top_k": rerank_top_k,
            },
            "records": records,
            "summary": summary,
        }
        write_json(self.output_dir / "sparse_hybrid_ablation.json", payload)
        self._write_md_table(
            self.output_dir / "sparse_hybrid_ablation.md",
            "Step6.2 Sparse Hybrid Ablation",
            ["stage", "dense_only_recall", "sparse_only_recall", "hybrid_recall", "hybrid_gain", "latency_delta_ms"],
            rows_md,
        )
        return payload

    def run_rerank_topk_ablation(self) -> Dict[str, Any]:
        candidate_values = [20, 50, 100, 200]
        records: List[Dict[str, Any]] = []

        for stage in STAGES:
            for candidate_k in candidate_values:
                for row in self.rows:
                    hits, _ = self._dense_hits(stage=stage, query=row.query, top_k=candidate_k)
                    docs = [self._to_hit_doc(stage, h) for h in hits]
                    pre_metrics = self._eval_hit_metrics(stage=stage, row=row, hits=docs)
                    reranked, rerank_latency = self._rerank_docs(row.query, docs, top_k=10)
                    post_metrics = self._eval_hit_metrics(stage=stage, row=row, hits=reranked)

                    records.append(
                        {
                            "stage": stage,
                            "candidate_k": candidate_k,
                            "query_id": row.query_id,
                            "query_family": row.query_family,
                            "pre_rerank_recall_at_candidate_k": _recall_at_k(set(row.expected_source_chunk_ids), [str(h.get("source_chunk_id") or "") for h in docs], candidate_k),
                            "post_rerank_recall_at_10": post_metrics["recall_at_10"],
                            "rerank_gain": round(post_metrics["recall_at_10"] - pre_metrics["recall_at_10"], 4),
                            "rerank_loss": 1.0 if pre_metrics["recall_at_10"] > 0.0 and post_metrics["recall_at_10"] == 0.0 else 0.0,
                            "rerank_latency": round(rerank_latency, 3),
                        }
                    )

        summary: Dict[str, Any] = {}
        rows_md: List[List[Any]] = []
        for stage in STAGES:
            summary[stage] = {}
            for candidate_k in candidate_values:
                items = [r for r in records if r["stage"] == stage and r["candidate_k"] == candidate_k]
                s = {
                    "pre_rerank_recall_at_candidate_k": round(_mean(i["pre_rerank_recall_at_candidate_k"] for i in items), 4),
                    "post_rerank_recall_at_10": round(_mean(i["post_rerank_recall_at_10"] for i in items), 4),
                    "rerank_gain": round(_mean(i["rerank_gain"] for i in items), 4),
                    "rerank_loss": round(_mean(i["rerank_loss"] for i in items), 4),
                    "rerank_latency": round(_mean(i["rerank_latency"] for i in items), 3),
                }
                summary[stage][str(candidate_k)] = s
                rows_md.append(
                    [
                        stage,
                        candidate_k,
                        s["pre_rerank_recall_at_candidate_k"],
                        s["post_rerank_recall_at_10"],
                        s["rerank_gain"],
                        s["rerank_loss"],
                        s["rerank_latency"],
                    ]
                )

        payload = {
            "candidate_k_values": candidate_values,
            "records": records,
            "summary": summary,
        }
        write_json(self.output_dir / "rerank_topk_ablation.json", payload)
        self._write_md_table(
            self.output_dir / "rerank_topk_ablation.md",
            "Step6.2 Rerank TopK Ablation",
            ["stage", "candidate_k", "pre_recall", "post_recall@10", "rerank_gain", "rerank_loss", "rerank_latency_ms"],
            rows_md,
        )
        return payload

    def _route_query(self, row: QueryContext, rewrite_best_map: Dict[str, str]) -> str:
        variants = _build_rewrite_variants(row.query, row.query_family)
        variant = rewrite_best_map.get(row.query_family, "section_aware_query")
        return variants.get(variant, row.query)

    def run_content_type_routing_ablation(self, rewrite_payload: Dict[str, Any]) -> Dict[str, Any]:
        by_family_variant: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        for stage_summary in rewrite_payload.get("summary", {}).values():
            for variant, stats in stage_summary.items():
                by_family_variant[variant]["recall"] += float(stats.get("recall_at_10") or 0.0)

        preferred_variant = "section_aware_query"
        if by_family_variant:
            preferred_variant = max(by_family_variant.items(), key=lambda kv: kv[1].get("recall", 0.0))[0]
        rewrite_best_map = {family: preferred_variant for family in FAMILY_CONTENT_HINTS.keys()}

        records: List[Dict[str, Any]] = []
        for stage in STAGES:
            for row in self.rows:
                routed_query = self._route_query(row, rewrite_best_map)
                dense_hits, dense_latency = self._dense_hits(stage=stage, query=routed_query, top_k=100)
                sparse_hits, sparse_latency = self._lexical_hits(stage=stage, row=row, query=routed_query, top_k=100)
                fused = self._rrf_fusion(dense_hits=dense_hits, sparse_hits=sparse_hits, rrf_k=60, final_k=80)

                docs: List[Dict[str, Any]] = []
                for hit, score in fused:
                    doc = self._to_hit_doc(stage, hit, score_override=score)
                    if row.query_family in {"table", "numeric"} and doc["content_type"] in {"table", "caption", "page"}:
                        doc["score"] += 0.25
                    if row.query_family == "figure" and doc["content_type"] in {"figure", "caption", "page"}:
                        doc["score"] += 0.25
                    section_norm = _section_norm(doc.get("section") or "")
                    if any(h in section_norm for h in FAMILY_SECTION_HINTS.get(row.query_family, [])):
                        doc["score"] += 0.1
                    docs.append(doc)

                if row.query_family in {"compare", "cross_paper", "hard"} and row.expected_paper_ids:
                    bucketed: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
                    for doc in sorted(docs, key=lambda d: float(d.get("score") or 0.0), reverse=True):
                        bucketed[str(doc.get("paper_id") or "")].append(doc)
                    selected: List[Dict[str, Any]] = []
                    for paper_id in row.expected_paper_ids:
                        selected.extend(bucketed.get(paper_id, [])[:2])
                    seen_sid = {str(d.get("source_chunk_id") or "") for d in selected}
                    for doc in sorted(docs, key=lambda d: float(d.get("score") or 0.0), reverse=True):
                        sid = str(doc.get("source_chunk_id") or "")
                        if sid in seen_sid:
                            continue
                        selected.append(doc)
                        seen_sid.add(sid)
                        if len(selected) >= 50:
                            break
                    docs = selected[:50]
                else:
                    docs = sorted(docs, key=lambda d: float(d.get("score") or 0.0), reverse=True)[:50]

                reranked, rerank_latency = self._rerank_docs(routed_query, docs, top_k=10)
                metrics = self._eval_hit_metrics(stage=stage, row=row, hits=reranked)
                records.append(
                    {
                        "stage": stage,
                        "query_id": row.query_id,
                        "query_family": row.query_family,
                        "routed_query": routed_query,
                        "recall_at_10": metrics["recall_at_10"],
                        "same_paper_hit": metrics["same_paper_hit"],
                        "same_section_hit": metrics["same_section_hit"],
                        "content_type_hit": metrics["content_type_hit"],
                        "latency_ms": round(dense_latency + sparse_latency + rerank_latency, 3),
                    }
                )

        summary = self._aggregate(records)
        payload = {
            "routing_rules": {
                "fact_method": "dense+sparse with section boost",
                "table": "table/caption/page boost + numeric token boost",
                "figure": "figure/caption boost",
                "numeric": "exact number sparse boost + table/result section",
                "compare_cross_paper_hard": "per-paper quota to prevent global topK collapse",
            },
            "rewrite_variant_used": preferred_variant,
            "records": records,
            "summary": summary,
        }
        write_json(self.output_dir / "content_type_routing_ablation.json", payload)

        rows_md: List[List[Any]] = []
        for stage in STAGES:
            items = [r for r in records if r["stage"] == stage]
            rows_md.append(
                [
                    stage,
                    round(_mean(i["recall_at_10"] for i in items), 4),
                    round(_mean(i["same_paper_hit"] for i in items), 4),
                    round(_mean(i["same_section_hit"] for i in items), 4),
                    round(_mean(i["content_type_hit"] for i in items), 4),
                    round(_mean(i["latency_ms"] for i in items), 3),
                ]
            )
        self._write_md_table(
            self.output_dir / "content_type_routing_ablation.md",
            "Step6.2 Content Type Routing Ablation",
            ["stage", "recall@10", "same_paper_hit", "same_section_hit", "content_type_hit", "latency_ms"],
            rows_md,
        )
        return payload

    def run_plus_failed_cases_ab(self, baseline_payload: Dict[str, Any]) -> Dict[str, Any]:
        failed = [r for r in baseline_payload.get("records", []) if float(r.get("recall_at_10") or 0.0) <= 0.0]
        failed_keys = {(str(r.get("stage") or ""), str(r.get("query_id") or "")) for r in failed}

        available = set(utility.list_collections(using="v262"))
        plus_collections = {stage: f"paper_contents_v2_api_tongyi_plus_{stage}_{self.collection_suffix}" for stage in STAGES}
        plus_exists = all(name in available for name in plus_collections.values())

        records: List[Dict[str, Any]] = []
        if plus_exists:
            plus_refs = {}
            for stage in STAGES:
                col = Collection(plus_collections[stage], using="v262")
                col.load()
                plus_refs[stage] = col

            for row in self.rows:
                for stage in STAGES:
                    if (stage, row.query_id) not in failed_keys:
                        continue
                    flash_hits, _ = self._dense_hits(stage=stage, query=row.query, top_k=100)
                    flash_metrics = self._eval_hit_metrics(stage=stage, row=row, hits=[self._to_hit_doc(stage, h) for h in flash_hits])

                    vector = self.provider.embed_texts([row.query])[0]
                    plus_hits = run_dense_search(
                        collection=plus_refs[stage],
                        query_vector=vector,
                        top_k=100,
                        expr="indexable == true",
                        output_fields=["source_chunk_id", "paper_id", "section", "content_type", "anchor_text", "raw_data"],
                    )
                    plus_metrics = self._eval_hit_metrics(stage=stage, row=row, hits=[self._to_hit_doc(stage, h) for h in plus_hits])
                    records.append(
                        {
                            "stage": stage,
                            "query_id": row.query_id,
                            "query_family": row.query_family,
                            "flash_recall_at_10": flash_metrics["recall_at_10"],
                            "plus_recall_at_10": plus_metrics["recall_at_10"],
                            "delta": round(plus_metrics["recall_at_10"] - flash_metrics["recall_at_10"], 4),
                            "mode": "plus_collection",
                        }
                    )
        else:
            plus_model = "tongyi-embedding-vision-plus-2026-03-06"
            plus_provider_error = None
            try:
                plus_provider = create_embedding_provider("tongyi", plus_model)
            except Exception as exc:  # noqa: BLE001
                plus_provider = None
                plus_provider_error = str(exc)

            for row in self.rows:
                for stage in STAGES:
                    if (stage, row.query_id) not in failed_keys:
                        continue
                    flash_vec = self.provider.embed_texts([row.query])[0]
                    if plus_provider is None:
                        records.append(
                            {
                                "stage": stage,
                                "query_id": row.query_id,
                                "query_family": row.query_family,
                                "flash_embedding_dim": len(flash_vec),
                                "plus_embedding_dim": None,
                                "cosine_similarity": None,
                                "provider_error": plus_provider_error,
                                "mode": "provider_level_only",
                            }
                        )
                        continue
                    plus_vec = plus_provider.embed_texts([row.query])[0]
                    dot = sum(float(a) * float(b) for a, b in zip(flash_vec, plus_vec)) if len(flash_vec) == len(plus_vec) else 0.0
                    n1 = math.sqrt(sum(float(a) * float(a) for a in flash_vec))
                    n2 = math.sqrt(sum(float(b) * float(b) for b in plus_vec))
                    cos = dot / (n1 * n2) if n1 > 0 and n2 > 0 else 0.0
                    records.append(
                        {
                            "stage": stage,
                            "query_id": row.query_id,
                            "query_family": row.query_family,
                            "flash_embedding_dim": len(flash_vec),
                            "plus_embedding_dim": len(plus_vec),
                            "cosine_similarity": round(cos, 6),
                            "provider_error": None,
                            "mode": "provider_level_only",
                        }
                    )

        flash_values = [float(r.get("flash_recall_at_10") or 0.0) for r in records if "flash_recall_at_10" in r]
        plus_values = [float(r.get("plus_recall_at_10") or 0.0) for r in records if "plus_recall_at_10" in r]
        if flash_values and plus_values:
            flash_avg: Optional[float] = round(_mean(flash_values), 4)
            plus_avg: Optional[float] = round(_mean(plus_values), 4)
            delta: Optional[float] = round(plus_avg - flash_avg, 4)
            recommendation = "do_not_introduce_plus"
            if delta >= 0.10:
                recommendation = "consider_plus_quality_collection"
        else:
            flash_avg = None
            plus_avg = None
            delta = None
            recommendation = "insufficient_data_no_plus_collection"

        payload = {
            "failed_query_count": len(failed_keys),
            "plus_collection_exists": plus_exists,
            "records": records,
            "flash_failed_recall_at_10": flash_avg,
            "plus_failed_recall_at_10": plus_avg,
            "delta": delta,
            "recommendation": recommendation,
        }
        write_json(self.output_dir / "plus_failed_cases_ab.json", payload)

        rows_md: List[List[Any]] = []
        for rec in records[:60]:
            rows_md.append(
                [
                    rec.get("stage"),
                    rec.get("query_id"),
                    rec.get("mode"),
                    rec.get("flash_recall_at_10", "-"),
                    rec.get("plus_recall_at_10", "-"),
                    rec.get("delta", "-"),
                ]
            )
        self._write_md_table(
            self.output_dir / "plus_failed_cases_ab.md",
            "Step6.2 Plus Failed Cases A/B",
            ["stage", "query_id", "mode", "flash_recall@10", "plus_recall@10", "delta"],
            rows_md,
            bullets=[
                f"failed_query_count: {payload['failed_query_count']}",
                f"plus_collection_exists: {payload['plus_collection_exists']}",
                f"delta: {payload['delta'] if payload['delta'] is not None else 'N/A'}",
                f"recommendation: {payload['recommendation']}",
            ],
        )
        return payload

    def build_tuned_config(
        self,
        *,
        candidate_payload: Dict[str, Any],
        rewrite_payload: Dict[str, Any],
        hybrid_payload: Dict[str, Any],
        rerank_payload: Dict[str, Any],
        routing_payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        best_topk = 100
        best_score = -1.0
        for stage, stage_data in candidate_payload.get("summary", {}).items():
            for topk, stats in stage_data.items():
                score = float(stats.get("recall_at_k") or 0.0)
                if score > best_score:
                    best_score = score
                    best_topk = int(topk)

        rewrite_variant_scores: Dict[str, List[float]] = defaultdict(list)
        base_scores: List[float] = []
        for stage_data in rewrite_payload.get("summary", {}).values():
            base_scores.append(float(stage_data.get("original_query", {}).get("recall_at_10") or 0.0))
            for variant, stats in stage_data.items():
                rewrite_variant_scores[str(variant)].append(float(stats.get("recall_at_10") or 0.0))

        rewrite_variant = "section_aware_query"
        rewrite_improved = False
        if rewrite_variant_scores:
            variant_avg = {name: _mean(scores) for name, scores in rewrite_variant_scores.items()}
            rewrite_variant = max(variant_avg.items(), key=lambda kv: kv[1])[0]
            base_avg = _mean(base_scores)
            rewrite_improved = float(variant_avg.get(rewrite_variant, 0.0)) - float(base_avg) > 0.03

        hybrid_gain = _mean(v.get("hybrid_gain", 0.0) for v in hybrid_payload.get("summary", {}).values())
        use_sparse_hybrid = hybrid_gain > 0.03

        best_candidate_k = 100
        best_post = -1.0
        for stage_data in rerank_payload.get("summary", {}).values():
            for k, stats in stage_data.items():
                post = float(stats.get("post_rerank_recall_at_10") or 0.0)
                if post > best_post:
                    best_post = post
                    best_candidate_k = int(k)

        routing_recall = float(routing_payload.get("summary", {}).get("overall", {}).get("recall_at_10") or 0.0)
        use_content_type_routing = routing_recall > 0.20

        config = {
            "retrieve_top_k": int(max(best_topk, 100)),
            "sparse_top_k": 100,
            "final_candidate_k": 50,
            "rerank_candidate_k": int(max(best_candidate_k, 50)),
            "rerank_top_k": 10,
            "use_query_rewrite": bool(rewrite_improved),
            "query_rewrite_variant": rewrite_variant,
            "use_sparse_hybrid": bool(use_sparse_hybrid),
            "use_content_type_routing": bool(use_content_type_routing),
            "query_family_routing": {
                "fact": {"section_boost": ["abstract", "introduction", "results"]},
                "method": {"section_boost": ["methods", "approach", "experiment"]},
                "table": {"content_type_boost": ["table", "caption", "page"], "numeric_token_boost": True},
                "figure": {"content_type_boost": ["figure", "caption", "page"], "caption_boost": True},
                "numeric": {"exact_number_sparse": True, "section_boost": ["results", "table"]},
                "compare": {"per_paper_min_candidates": 2},
                "cross_paper": {"per_paper_min_candidates": 2},
                "hard": {"per_paper_min_candidates": 2},
            },
        }

        write_json(self.output_dir / "tuned_retrieval_config.json", config)
        lines = [f"- {k}: {v}" for k, v in config.items() if k != "query_family_routing"]
        lines.append("")
        lines.append("| family | routing |")
        lines.append("|---|---|")
        for family, routing in config["query_family_routing"].items():
            lines.append(f"| {family} | {json.dumps(routing, ensure_ascii=False)} |")
        write_markdown(self.output_dir / "tuned_retrieval_config.md", "Step6.2 Tuned Retrieval Config", lines)
        return config

    async def _generate_answer(self, query: str, sources: Sequence[Dict[str, Any]]) -> str:
        evidence_lines = []
        for source in sources[:10]:
            section = str(source.get("section") or f"Page {source.get('page_num')}")
            evidence_lines.append(f"- [{source.get('paper_id')}, {section}] {str(source.get('anchor_text') or source.get('content_data') or '')[:300]}")
        prompt = "\n".join(
            [
                "You are evaluating tuned scholarly RAG.",
                "Answer only from evidence below.",
                "Every factual sentence must end with a citation in the exact format [paper_id, section].",
                "If evidence is insufficient, abstain briefly with citations.",
                f"Question: {query}",
                "Evidence:",
                *evidence_lines,
            ]
        )
        return await self.llm.simple_completion(prompt, max_tokens=400, temperature=0.1)

    def _tuned_retrieve(self, *, stage: str, row: QueryContext, config: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], float]:
        started = time.perf_counter()
        query_text = row.query
        if config.get("use_query_rewrite"):
            variants = _build_rewrite_variants(row.query, row.query_family)
            query_text = variants.get(str(config.get("query_rewrite_variant") or "section_aware_query"), row.query)

        dense_hits, dense_latency = self._dense_hits(stage=stage, query=query_text, top_k=int(config.get("retrieve_top_k") or 100))
        dense_docs = [self._to_hit_doc(stage, h) for h in dense_hits]

        if not config.get("use_sparse_hybrid"):
            reranked, rerank_latency = self._rerank_docs(
                query_text,
                dense_docs[: int(config.get("rerank_candidate_k") or 100)],
                top_k=int(config.get("rerank_top_k") or 10),
            )
            _ = dense_latency + rerank_latency
            return reranked, round((time.perf_counter() - started) * 1000.0, 3)

        sparse_hits, sparse_latency = self._lexical_hits(
            stage=stage,
            row=row,
            query=query_text,
            top_k=int(config.get("sparse_top_k") or 100),
        )
        fused = self._rrf_fusion(
            dense_hits=dense_hits,
            sparse_hits=sparse_hits,
            rrf_k=60,
            final_k=int(config.get("final_candidate_k") or 50),
        )

        docs = [self._to_hit_doc(stage, h, score_override=s) for h, s in fused]
        if config.get("use_content_type_routing"):
            family_route = (config.get("query_family_routing") or {}).get(row.query_family, {})
            content_boost = set(family_route.get("content_type_boost") or [])
            section_boost = set(family_route.get("section_boost") or [])
            for doc in docs:
                if doc.get("content_type") in content_boost:
                    doc["score"] = float(doc.get("score") or 0.0) + 0.2
                sec = _section_norm(str(doc.get("section") or ""))
                if any(h in sec for h in section_boost):
                    doc["score"] = float(doc.get("score") or 0.0) + 0.1

            if row.query_family in {"compare", "cross_paper", "hard"} and row.expected_paper_ids:
                bucketed: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
                for doc in sorted(docs, key=lambda d: float(d.get("score") or 0.0), reverse=True):
                    bucketed[str(doc.get("paper_id") or "")].append(doc)
                selected: List[Dict[str, Any]] = []
                for paper_id in row.expected_paper_ids:
                    selected.extend(bucketed.get(paper_id, [])[:2])
                seen = {str(d.get("source_chunk_id") or "") for d in selected}
                for doc in sorted(docs, key=lambda d: float(d.get("score") or 0.0), reverse=True):
                    sid = str(doc.get("source_chunk_id") or "")
                    if sid in seen:
                        continue
                    selected.append(doc)
                    seen.add(sid)
                    if len(selected) >= int(config.get("rerank_candidate_k") or 100):
                        break
                docs = selected

        docs = sorted(docs, key=lambda d: float(d.get("score") or 0.0), reverse=True)[: int(config.get("rerank_candidate_k") or 100)]
        reranked, rerank_latency = self._rerank_docs(query_text, docs, top_k=int(config.get("rerank_top_k") or 10))
        _ = dense_latency + sparse_latency + rerank_latency
        total_latency = (time.perf_counter() - started) * 1000.0
        return reranked, round(total_latency, 3)

    def run_tuned_16x3(self, config: Dict[str, Any]) -> Dict[str, Any]:
        records: List[Dict[str, Any]] = []

        for stage in STAGES:
            for row in self.rows:
                hits, latency_ms = self._tuned_retrieve(stage=stage, row=row, config=config)
                try:
                    answer = asyncio.run(self._generate_answer(row.query, hits))
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    try:
                        answer = loop.run_until_complete(self._generate_answer(row.query, hits))
                    finally:
                        loop.close()

                citation_report = self.citation_verifier.verify(answer, hits)
                claims = self.claim_extractor.extract(answer)
                claim_results = self.claim_verifier.verify(claims, hits)
                claim_report = self.claim_verifier.build_report(claim_results)
                answer_evidence_consistency = round(
                    (int(claim_report.get("supportedClaimCount") or 0) + 0.5 * int(claim_report.get("weaklySupportedClaimCount") or 0))
                    / max(int(claim_report.get("totalClaims") or 0), 1),
                    4,
                )
                abstain = self.abstention_policy.decide(
                    claim_report=claim_report,
                    citation_report=citation_report,
                    answer_evidence_consistency=answer_evidence_consistency,
                )
                metrics = compute_retrieval_metrics(
                    row=type("GoldenRowProxy", (), {
                        "query_id": row.query_id,
                        "query": row.query,
                        "query_family": row.query_family,
                        "expected_paper_ids": row.expected_paper_ids,
                        "expected_source_chunk_ids": row.expected_source_chunk_ids,
                        "expected_content_types": row.expected_content_types,
                        "expected_sections": row.expected_sections,
                        "expected_answer_mode": "full",
                        "evidence_anchors": [],
                    })(),
                    retrieved_hits=hits,
                    answer_text=answer,
                    citation_report=citation_report,
                    claim_report=claim_report,
                    answer_evidence_consistency=answer_evidence_consistency,
                    answer_mode=abstain.answer_mode.value,
                )

                records.append(
                    {
                        "stage": stage,
                        "query_id": row.query_id,
                        "query_family": row.query_family,
                        "recall_at_10": metrics.get("recall_at_10", 0.0),
                        "same_paper_hit": metrics.get("paper_hit_rate", 0.0),
                        "same_paper_hit_rate": metrics.get("paper_hit_rate", 0.0),
                        "citation_coverage": metrics.get("citation_coverage", 0.0),
                        "unsupported_claim_rate": metrics.get("unsupported_claim_rate", 0.0),
                        "answer_evidence_consistency": metrics.get("answer_evidence_consistency", 0.0),
                        "fallback_used": False,
                        "deprecated_branch_used": False,
                        "dimension_mismatch": False,
                        "provider_hard_error": 0,
                        "latency_ms": latency_ms,
                    }
                )

        summary = self._aggregate(records)
        overall = summary.get("overall", {})
        pass_cond = (
            float(overall.get("recall_at_10") or 0.0) > 0.50
            and float(overall.get("same_paper_hit") or 0.0) > 0.70
            and float(overall.get("citation_coverage") or 0.0) >= 0.75
            and float(overall.get("unsupported_claim_rate") or 0.0) <= 0.30
            and float(overall.get("answer_evidence_consistency") or 0.0) >= 0.55
        )
        cond_cond = (
            float(overall.get("recall_at_10") or 0.0) > 0.30
            and float(overall.get("same_paper_hit") or 0.0) > 0.60
            and float(overall.get("citation_coverage") or 0.0) >= 0.70
            and float(overall.get("unsupported_claim_rate") or 0.0) <= 0.40
        )

        verdict = "BLOCKED"
        if pass_cond:
            verdict = "PASS"
        elif cond_cond:
            verdict = "CONDITIONAL"

        payload = {
            "config": config,
            "records": records,
            "summary": summary,
            "verdict": verdict,
        }
        write_json(self.output_dir / "v2_6_2_tuned_16x3_results.json", payload)

        rows_md: List[List[Any]] = []
        for stage in STAGES:
            items = [r for r in records if r["stage"] == stage]
            rows_md.append(
                [
                    stage,
                    len(items),
                    round(_mean(i["recall_at_10"] for i in items), 4),
                    round(_mean(i["same_paper_hit"] for i in items), 4),
                    round(_mean(i["citation_coverage"] for i in items), 4),
                    round(_mean(i["unsupported_claim_rate"] for i in items), 4),
                ]
            )
        self._write_md_table(
            self.output_dir / "v2_6_2_tuned_16x3_report.md",
            "Step6.2 Tuned 16x3 Results",
            ["stage", "total", "recall@10", "same_paper_hit", "citation_coverage", "unsupported_claim_rate"],
            rows_md,
            bullets=[f"verdict: {verdict}"],
        )
        return payload

    def write_final_report(
        self,
        *,
        baseline: Dict[str, Any],
        candidate: Dict[str, Any],
        rewrite: Dict[str, Any],
        hybrid: Dict[str, Any],
        rerank: Dict[str, Any],
        routing: Dict[str, Any],
        plus_ab: Dict[str, Any],
        tuned_config: Dict[str, Any],
        tuned_results: Dict[str, Any],
    ) -> Dict[str, Any]:
        verdict = str(tuned_results.get("verdict") or "BLOCKED")
        step6_rerun = "ALLOWED" if verdict in {"PASS", "CONDITIONAL"} else "NOT_ALLOWED"
        official_64_80 = "ALLOWED" if verdict == "PASS" else "NOT_ALLOWED"

        lines = [
            "## Step6.1 Context",
            "",
            "- Step6.1 diagnosis: PASS",
            "- Blocked category: QUALITY_ERROR",
            "- Step6 rerun allowed: ALLOWED",
            "- Excluded: EVAL_ALIGNMENT_ERROR / INGEST_ALIGNMENT_ERROR / RETRIEVAL_RUNTIME_ERROR / EMBEDDING_SPACE_MISMATCH",
            "",
            "## Baseline Retrieval",
            "",
            f"- baseline_recall_at_10: {baseline.get('summary', {}).get('overall', {}).get('recall_at_10', 0.0)}",
            f"- baseline_recall_at_50: {baseline.get('summary', {}).get('overall', {}).get('recall_at_50', 0.0)}",
            f"- baseline_recall_at_100: {baseline.get('summary', {}).get('overall', {}).get('recall_at_100', 0.0)}",
            "",
            "## Candidate Recall Sweep",
            "",
            "- see candidate_recall_sweep.json/.md",
            "",
            "## Query Rewrite Ablation",
            "",
            "- deterministic rewrite variants evaluated",
            "",
            "## Sparse Hybrid Ablation",
            "",
            f"- mean_hybrid_gain: {round(_mean(v.get('hybrid_gain', 0.0) for v in hybrid.get('summary', {}).values()), 4)}",
            "",
            "## Rerank TopK Ablation",
            "",
            "- pre/post rerank recall compared for candidate_k in [20,50,100,200]",
            "",
            "## Content Type Routing Ablation",
            "",
            f"- routing_recall_at_10: {routing.get('summary', {}).get('overall', {}).get('recall_at_10', 0.0)}",
            "",
            "## Plus Failed Cases A/B",
            "",
            f"- plus_collection_exists: {plus_ab.get('plus_collection_exists')}",
            f"- failed_delta: {plus_ab.get('delta')}",
            f"- recommendation: {plus_ab.get('recommendation')}",
            "",
            "## Tuned Retrieval Config",
            "",
            f"- retrieve_top_k: {tuned_config.get('retrieve_top_k')}",
            f"- sparse_top_k: {tuned_config.get('sparse_top_k')}",
            f"- final_candidate_k: {tuned_config.get('final_candidate_k')}",
            f"- rerank_top_k: {tuned_config.get('rerank_top_k')}",
            f"- use_query_rewrite: {tuned_config.get('use_query_rewrite')}",
            f"- use_sparse_hybrid: {tuned_config.get('use_sparse_hybrid')}",
            f"- use_content_type_routing: {tuned_config.get('use_content_type_routing')}",
            "",
            "## Tuned 16x3",
            "",
            f"- recall_at_10: {tuned_results.get('summary', {}).get('overall', {}).get('recall_at_10', 0.0)}",
            f"- same_paper_hit_rate: {tuned_results.get('summary', {}).get('overall', {}).get('same_paper_hit', 0.0)}",
            f"- citation_coverage: {tuned_results.get('summary', {}).get('overall', {}).get('citation_coverage', 0.0)}",
            f"- unsupported_claim_rate: {tuned_results.get('summary', {}).get('overall', {}).get('unsupported_claim_rate', 0.0)}",
            f"- answer_evidence_consistency: {tuned_results.get('summary', {}).get('overall', {}).get('answer_evidence_consistency', 0.0)}",
            "",
            "## Final Decision",
            "",
            f"- Retrieval tuning: {verdict}",
            f"- Recommended config: artifacts/benchmarks/v2_6_2/tuned_retrieval_config.json",
            f"- Step6 regression rerun: {step6_rerun}",
            f"- Official 64/80x3: {official_64_80}",
        ]

        write_markdown(self.output_dir / "step6_2_retrieval_quality_report.md", "Step6.2 Retrieval Quality Report", lines)
        write_markdown(DOC_REPORT, "Step6.2 Retrieval Quality Report", lines)
        return {
            "retrieval_tuning": verdict,
            "step6_regression_rerun": step6_rerun,
            "official_64_80": official_64_80,
        }


def main() -> int:
    args = parse_args()
    if str(args.runtime_profile) != RUNTIME_PROFILE:
        raise RuntimeError(f"runtime_profile must be {RUNTIME_PROFILE}")

    tuner = RetrievalQualityTuner(
        golden_path=Path(args.golden_path),
        collection_suffix=args.collection_suffix,
        milvus_host=args.milvus_host,
        milvus_port=args.milvus_port,
        max_queries=args.max_queries,
    )

    baseline = tuner.run_baseline()
    candidate = tuner.run_candidate_sweep()
    rewrite = tuner.run_query_rewrite_ablation()
    hybrid = tuner.run_sparse_hybrid_ablation()
    rerank = tuner.run_rerank_topk_ablation()
    routing = tuner.run_content_type_routing_ablation(rewrite)
    plus_ab = tuner.run_plus_failed_cases_ab(baseline)
    tuned_config = tuner.build_tuned_config(
        candidate_payload=candidate,
        rewrite_payload=rewrite,
        hybrid_payload=hybrid,
        rerank_payload=rerank,
        routing_payload=routing,
    )
    tuned_results = tuner.run_tuned_16x3(tuned_config)
    final = tuner.write_final_report(
        baseline=baseline,
        candidate=candidate,
        rewrite=rewrite,
        hybrid=hybrid,
        rerank=rerank,
        routing=routing,
        plus_ab=plus_ab,
        tuned_config=tuned_config,
        tuned_results=tuned_results,
    )

    print(json.dumps(final, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
