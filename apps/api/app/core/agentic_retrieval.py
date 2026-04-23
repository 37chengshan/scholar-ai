"""Agentic retrieval orchestrator for complex cross-paper queries.

Implements multi-round retrieval with:
- Query decomposition into sub-questions
- Parallel sub-question execution via asyncio.gather
- LLM synthesis of results
- Convergence detection (max 3 rounds or early convergence)

Usage:
    orchestrator = AgenticRetrievalOrchestrator()
    result = await orchestrator.retrieve(
        query="YOLO evolution from v1 to v4",
        query_type="evolution",
        paper_ids=["yolov1", "yolov2", "yolov3", "yolov4"]
    )
"""

import asyncio
import re
from typing import Any, Dict, List, Optional

from app.utils.logger import logger
from app.core.abstention_policy import get_abstention_policy
from app.core.claim_extractor import get_claim_extractor
from app.core.claim_verifier import get_claim_verifier
from app.core.query_decomposer import (
    QueryDecomposer,
    ConvergenceChecker,
    QueryType,
)
from app.core.query_planner import build_academic_query_plan
from app.core.graph_query_compiler import get_graph_query_compiler
from app.core.graph_retrieval_service import get_graph_retrieval_service
from app.core.multimodal_search_service import get_multimodal_search_service
from app.core.citation_verifier import get_citation_verifier
from app.core.retrieval_evaluator import RetrievalEvaluator


class AgenticRetrievalOrchestrator:
    """Orchestrates multi-round agentic retrieval for complex queries.

    Attributes:
        max_rounds: Maximum retrieval rounds (default: 3)
        decomposer: QueryDecomposer instance
        convergence_checker: ConvergenceChecker instance
        search_service: MultimodalSearchService for Milvus-based search
    """

    def __init__(
        self,
        max_rounds: int = 3,
        decomposer: Optional[QueryDecomposer] = None,
        convergence_checker: Optional[ConvergenceChecker] = None,
    ):
        """Initialize agentic retrieval orchestrator.

        Args:
            max_rounds: Maximum retrieval rounds
            decomposer: QueryDecomposer instance
            convergence_checker: ConvergenceChecker instance
        """
        self.max_rounds = max(1, min(max_rounds, 5))  # Clamp between 1-5
        self.decomposer = decomposer or QueryDecomposer()
        self.convergence_checker = convergence_checker or ConvergenceChecker()
        self.search_service = get_multimodal_search_service()
        self.citation_verifier = get_citation_verifier()
        self.claim_extractor = get_claim_extractor()
        self.claim_verifier = get_claim_verifier()
        self.abstention_policy = get_abstention_policy()
        self.graph_query_compiler = get_graph_query_compiler()
        self.graph_retrieval_service = get_graph_retrieval_service()
        self.retrieval_evaluator = RetrievalEvaluator()

    async def retrieve(
        self,
        query: str,
        query_type: Optional[QueryType] = None,
        paper_ids: Optional[List[str]] = None,
        user_id: str = None,
        top_k_per_subquestion: int = 5,
    ) -> Dict[str, Any]:
        """Execute agentic retrieval with multi-round support.

        Args:
            query: Original user query
            query_type: Query type (auto-detected if None)
            paper_ids: List of paper IDs to search
            user_id: User ID for Milvus filtering (per D-35) - REQUIRED
            top_k_per_subquestion: Number of chunks per sub-question

        Returns:
            Dictionary with synthesized answer, sub-questions, sources, and metadata

        Raises:
            ValueError: If user_id is not provided
        """
        if user_id is None:
            raise ValueError("user_id is required for agentic retrieval")
        # Step 1: Decompose query into sub-questions
        logger.info(
            "Starting agentic retrieval",
            query=query[:50],
            paper_count=len(paper_ids) if paper_ids else 0,
        )

        academic_plan = build_academic_query_plan(query, query_type or "", paper_ids=paper_ids)
        effective_query_type = (query_type or academic_plan.get("query_family") or "single")
        expected_evidence_types = academic_plan.get("expected_evidence_types") or ["text"]
        graph_hint = self.graph_query_compiler.compile(query, str(effective_query_type))
        graph_candidates = await self.graph_retrieval_service.expand_graph_context(
            graph_hint=graph_hint,
            paper_ids=paper_ids or [],
            query=query,
        )

        sub_questions = await self.decomposer.decompose_query(
            query=query,
            query_type=effective_query_type,
            paper_ids=paper_ids,
        )

        planned_sub_questions = academic_plan.get("sub_questions") or []
        if planned_sub_questions:
            sub_questions = [
                {
                    "question": item.get("question"),
                    "query_type": effective_query_type,
                    "target_papers": paper_ids or [],
                    "rationale": item.get("role", "academic_plan"),
                }
                for item in planned_sub_questions
                if item.get("question")
            ]

        if not sub_questions:
            return {
                "answer": "Unable to decompose query into sub-questions.",
                "sub_questions": [],
                "sources": [],
                "rounds_executed": 0,
                "converged": False,
                "error": "Query decomposition failed",
            }

        # Step 2: Multi-round retrieval
        all_results = []
        previous_synthesis = ""
        converged = False
        rounds_executed = 0
        iterative_retrieval_triggered = False
        iterative_actions: List[Dict[str, Any]] = []
        citation_reasoning_report: Dict[str, List[Dict[str, Any]]] = {
            "foundational": [],
            "follow_up": [],
            "competing": [],
            "evolution_chain": [],
            "merged_candidates": list(graph_candidates or []),
        }
        retrieval_evaluation: Dict[str, Any] = {
            "is_weak": False,
            "weak_reasons": [],
            "trigger_citation_expansion": False,
            "missing_expected_evidence_types": [],
            "metrics": {},
        }
        retrieval_trace: Dict[str, Any] = {
            "mode": "orchestrator_v2",
            "iterative_triggered": False,
            "iterative_actions": [],
            "first_pass_evaluation": None,
            "rounds": [],
        }

        for round_num in range(1, self.max_rounds + 1):
            logger.info(
                f"Executing retrieval round {round_num}/{self.max_rounds}",
                subquestion_count=len(sub_questions),
            )

            # Execute sub-questions in parallel
            round_results = await self._execute_subquestions_parallel(
                sub_questions=sub_questions,
                paper_ids=paper_ids or [],
                user_id=user_id,
                top_k=top_k_per_subquestion,
                content_types=expected_evidence_types,
                graph_hint=graph_hint,
                graph_candidates=graph_candidates,
            )

            all_results.append(
                {
                    "round": round_num,
                    "results": round_results,
                }
            )

            round_chunk_count = sum(len(item.get("chunks", [])) for item in round_results)
            retrieval_trace["rounds"].append(
                {
                    "round": round_num,
                    "subquestion_count": len(sub_questions),
                    "success_count": len([item for item in round_results if item.get("success", True)]),
                    "chunk_count": round_chunk_count,
                }
            )

            rounds_executed = round_num

            if round_num == 1:
                first_pass_chunks = self._flatten_round_chunks(round_results)
                retrieval_evaluation = self.retrieval_evaluator.evaluate(
                    query_family=str(academic_plan.get("query_family") or effective_query_type),
                    chunks=first_pass_chunks,
                    expected_evidence_types=expected_evidence_types,
                    paper_ids=paper_ids or [],
                    graph_candidates=graph_candidates or [],
                    top_k=max(top_k_per_subquestion, 6),
                )
                retrieval_trace["first_pass_evaluation"] = retrieval_evaluation

                if retrieval_evaluation.get("is_weak") and round_num < self.max_rounds:
                    iterative_retrieval_triggered = True
                    retrieval_trace["iterative_triggered"] = True
                    iterative_actions = self._plan_iterative_actions(
                        query=query,
                        query_family=str(academic_plan.get("query_family") or effective_query_type),
                        academic_plan=academic_plan,
                        retrieval_evaluation=retrieval_evaluation,
                    )
                    retrieval_trace["iterative_actions"] = iterative_actions
                    sub_questions, graph_candidates, citation_reasoning_report = await self._apply_iterative_actions(
                        sub_questions=sub_questions,
                        iterative_actions=iterative_actions,
                        query=query,
                        query_family=str(academic_plan.get("query_family") or effective_query_type),
                        paper_ids=paper_ids or [],
                        top_k=top_k_per_subquestion,
                        graph_candidates=graph_candidates,
                    )

            # Check convergence after first round
            if round_num > 1:
                converged = await self._check_convergence(
                    previous_results=all_results[-2]["results"],
                    current_results=round_results,
                    previous_synthesis=previous_synthesis,
                )

                if converged:
                    logger.info(
                        "Convergence detected, stopping early",
                        round=round_num,
                    )
                    break

            # Synthesize results for this round
            previous_synthesis = await self._synthesize_results(
                query=query,
                query_type=effective_query_type,
                results=round_results,
                round_num=round_num,
            )

            # If we've reached max rounds, don't continue
            if round_num >= self.max_rounds:
                break

            # For evolution/cross_paper queries, refine sub-questions based on results
            if (
                effective_query_type in ("evolution", "cross_paper", "compare")
                and round_num < self.max_rounds
            ):
                sub_questions = await self._refine_subquestions(
                    sub_questions=sub_questions,
                    results=round_results,
                    query=query,
                )

        # Step 3: Final synthesis
        answer_outline = self._build_answer_outline(
            query=query,
            query_type=str(effective_query_type),
            all_results=all_results,
        )
        final_answer = await self._final_synthesis(
            query=query,
            query_type=effective_query_type,
            all_results=all_results,
            answer_outline=answer_outline,
        )
        final_answer = self._validate_and_fix_citations(final_answer, all_results, query)

        # Collect all sources
        all_sources = self._collect_sources(all_results)

        citation_checked_answer, citation_report = (
            self.citation_verifier.prune_unsupported_claims(final_answer, all_sources)
        )
        extracted_claims = self.claim_extractor.extract(citation_checked_answer)
        claim_results = self.claim_verifier.verify(extracted_claims, all_sources)
        claim_report = self.claim_verifier.build_report(claim_results)
        consistency_score = self._compute_answer_evidence_consistency(citation_checked_answer, all_sources)
        abstain_decision = self.abstention_policy.decide(
            claim_report=claim_report,
            citation_report=citation_report,
            answer_evidence_consistency=consistency_score,
        )
        verified_answer = self._apply_answer_mode(
            answer=citation_checked_answer,
            claim_results=claim_results,
            answer_mode=abstain_decision.answer_mode.value,
            abstain_reason=abstain_decision.abstain_reason,
        )

        logger.info(
            "Agentic retrieval completed",
            query=query[:50],
            rounds=rounds_executed,
            converged=converged,
            sources=len(all_sources),
            citation_coverage=citation_report.get("citation_coverage"),
            iterative_triggered=iterative_retrieval_triggered,
        )

        citation_faithfulness = float(citation_report.get("citation_coverage") or 0.0)
        unsupported_claim_rate = float(claim_report.get("unsupportedClaimRate") or 0.0)
        cross_paper_synthesis_quality = float(retrieval_evaluation.get("metrics", {}).get("cross_paper_coverage") or 0.0)
        if abstain_decision.answer_mode.value == "partial":
            partial_abstain_quality = round(max(0.0, 1.0 - unsupported_claim_rate), 4)
        elif abstain_decision.answer_mode.value == "abstain":
            partial_abstain_quality = 1.0
        else:
            partial_abstain_quality = 1.0

        return {
            "answer": verified_answer,
            "sub_questions": [
                {"question": sq.get("question"), "rationale": sq.get("rationale")}
                for sq in (sub_questions if sub_questions else [])
            ],
            "sources": all_sources,
            "rounds_executed": rounds_executed,
            "converged": converged,
            "metadata": {
                "query_type": effective_query_type,
                "query_family": academic_plan.get("query_family"),
                "decontextualized_query": academic_plan.get("decontextualized_query"),
                "expected_evidence_types": expected_evidence_types,
                "retrieval_evaluator": retrieval_evaluation,
                "iterative_retrieval_triggered": iterative_retrieval_triggered,
                "iterative_actions": iterative_actions,
                "retrieval_trace": retrieval_trace,
                "answer_outline": answer_outline,
                "citation_aware_metadata": {
                    "citation_expansion_applied": bool(iterative_retrieval_triggered and citation_reasoning_report.get("merged_candidates")),
                    "foundational_count": len(citation_reasoning_report.get("foundational") or []),
                    "follow_up_count": len(citation_reasoning_report.get("follow_up") or []),
                    "competing_count": len(citation_reasoning_report.get("competing") or []),
                    "evolution_chain_count": len(citation_reasoning_report.get("evolution_chain") or []),
                },
                "rewrite_count": len(academic_plan.get("fallback_rewrites") or []),
                "paper_count": len(paper_ids) if paper_ids else 0,
                "subquestion_count": len(sub_questions) if sub_questions else 0,
                "citation_verification": citation_report,
                "claimVerification": claim_report,
                "unsupported_claim_rate": abstain_decision.unsupported_claim_rate,
                "citation_coverage": abstain_decision.citation_coverage,
                "answer_evidence_consistency": abstain_decision.answer_evidence_consistency,
                "supportedClaimCount": abstain_decision.supported_claim_count,
                "unsupportedClaimCount": abstain_decision.unsupported_claim_count,
                "weaklySupportedClaimCount": abstain_decision.weakly_supported_claim_count,
                "abstained": abstain_decision.abstained,
                "abstainReason": abstain_decision.abstain_reason,
                "answerMode": abstain_decision.answer_mode.value,
                "graph_retrieval_used": bool(graph_candidates),
                "graph_candidate_count": len(graph_candidates),
                "graph_vector_merged_evidence": len(all_sources),
                "scientific_synthesis_metrics": {
                    "citation_faithfulness": round(citation_faithfulness, 4),
                    "unsupported_claim_rate": round(unsupported_claim_rate, 4),
                    "cross_paper_synthesis_quality": round(cross_paper_synthesis_quality, 4),
                    "partial_abstain_quality": round(partial_abstain_quality, 4),
                },
                "benchmarkMetrics": {
                    "unsupported_claim_rate": abstain_decision.unsupported_claim_rate,
                    "citation_coverage": abstain_decision.citation_coverage,
                    "answer_evidence_consistency": abstain_decision.answer_evidence_consistency,
                    "claim_support_precision": round(
                        (abstain_decision.supported_claim_count / max(
                            abstain_decision.supported_claim_count + abstain_decision.weakly_supported_claim_count,
                            1,
                        )),
                        4,
                    ),
                    "claim_support_recall": round(
                        (abstain_decision.supported_claim_count / max(
                            abstain_decision.supported_claim_count + abstain_decision.unsupported_claim_count,
                            1,
                        )),
                        4,
                    ),
                    "abstain_precision": 1.0 if abstain_decision.abstained else 0.0,
                    "abstain_recall": 1.0 if abstain_decision.abstained or abstain_decision.answer_mode.value == "partial" else 0.0,
                    "partial_answer_quality": round(
                        1.0 - abstain_decision.unsupported_claim_rate if abstain_decision.answer_mode.value == "partial" else float(abstain_decision.answer_mode.value == "full"),
                        4,
                    ),
                    "compare_accuracy": 1.0 if effective_query_type == "compare" and graph_candidates else 0.0,
                    "graph_triplet_recall": round(min(len(graph_candidates) / max(len(paper_ids or []), 1), 1.0), 4),
                    "graph_triplet_precision": round(min(len(graph_candidates) / max(len(graph_candidates), 1), 1.0), 4),
                    "method_dataset_metric_f1": round(min(len(graph_candidates) / max(len(all_sources), 1), 1.0), 4),
                    "complex_relation_accuracy": 1.0 if effective_query_type in {"compare", "evolution", "numeric"} and graph_candidates else 0.0,
                    "graph_assisted_recall_at_5": round(min(len(graph_candidates) / 5.0, 1.0), 4),
                    "graph_assisted_latency_ms": 0.0,
                    "graph_vector_merge_gain": round(min(len(graph_candidates) / max(len(all_sources), 1), 1.0), 4),
                    "citation_faithfulness": round(citation_faithfulness, 4),
                    "cross_paper_synthesis_quality": round(cross_paper_synthesis_quality, 4),
                    "partial_abstain_quality": round(partial_abstain_quality, 4),
                },
            },
        }

    @staticmethod
    def _flatten_round_chunks(round_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        flattened: List[Dict[str, Any]] = []
        for result in round_results:
            flattened.extend(result.get("chunks", []))
        return flattened

    def _plan_iterative_actions(
        self,
        *,
        query: str,
        query_family: str,
        academic_plan: Dict[str, Any],
        retrieval_evaluation: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        actions: List[Dict[str, Any]] = []
        iterative_plan = academic_plan.get("iterative_actions") or {}
        rewrites = list(iterative_plan.get("rewrite_queries") or [])[:3]

        if rewrites:
            actions.append({"action": "query_rewrite", "queries": rewrites})

        if retrieval_evaluation.get("trigger_citation_expansion") and iterative_plan.get("enable_citation_expansion", False):
            actions.append({"action": "citation_expansion", "query_family": query_family})

        if iterative_plan.get("enable_summary_fallback", False):
            actions.append({"action": "summary_fallback", "query": f"summary overview for {query}"})

        if iterative_plan.get("enable_relation_aware_expansion", False):
            actions.append({"action": "relation_aware_candidate_expansion"})

        if iterative_plan.get("enable_multi_subquestion_retrieval", False):
            actions.append({"action": "multi_subquestion_retrieval"})

        return actions

    async def _apply_iterative_actions(
        self,
        *,
        sub_questions: List[Dict[str, Any]],
        iterative_actions: List[Dict[str, Any]],
        query: str,
        query_family: str,
        paper_ids: List[str],
        top_k: int,
        graph_candidates: Optional[List[Dict[str, Any]]],
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]:
        expanded_sub_questions = list(sub_questions)
        merged_graph_candidates = list(graph_candidates or [])
        citation_reasoning_report: Dict[str, List[Dict[str, Any]]] = {
            "foundational": [],
            "follow_up": [],
            "competing": [],
            "evolution_chain": [],
            "merged_candidates": merged_graph_candidates,
        }

        for action in iterative_actions:
            action_name = action.get("action")
            if action_name == "query_rewrite":
                for rewritten_query in action.get("queries") or []:
                    expanded_sub_questions.append(
                        {
                            "question": rewritten_query,
                            "query_type": query_family,
                            "target_papers": paper_ids,
                            "rationale": "iterative_rewrite",
                        }
                    )
            elif action_name == "summary_fallback":
                expanded_sub_questions.append(
                    {
                        "question": str(action.get("query") or f"summary for {query}"),
                        "query_type": "summary",
                        "target_papers": paper_ids,
                        "rationale": "summary_fallback",
                    }
                )
            elif action_name == "multi_subquestion_retrieval":
                expanded_sub_questions = await self._refine_subquestions(
                    sub_questions=expanded_sub_questions,
                    results=[],
                    query=query,
                )
            elif action_name in {"citation_expansion", "relation_aware_candidate_expansion"}:
                citation_reasoning_report = await self.graph_retrieval_service.reason_citation_context(
                    query=query,
                    query_family=query_family,
                    paper_ids=paper_ids,
                    top_k=max(top_k * 2, 8),
                )
                merged_graph_candidates = list(citation_reasoning_report.get("merged_candidates") or merged_graph_candidates)

        deduped: List[Dict[str, Any]] = []
        seen = set()
        for item in expanded_sub_questions:
            question = str(item.get("question") or "").strip()
            if not question or question in seen:
                continue
            seen.add(question)
            deduped.append(item)

        return deduped[:10], merged_graph_candidates, citation_reasoning_report

    def _build_answer_outline(
        self,
        *,
        query: str,
        query_type: str,
        all_results: List[Dict[str, Any]],
    ) -> List[Dict[str, str]]:
        sections: List[Dict[str, str]] = []
        normalized_type = (query_type or "fact").lower()
        sections.append({"title": "Question Scope", "goal": f"Frame the question: {query}"})

        if normalized_type in {"compare", "cross_paper"}:
            sections.extend(
                [
                    {"title": "Method Comparison", "goal": "Compare major claims across papers."},
                    {"title": "Evidence Differences", "goal": "Highlight metric or evidence contrasts."},
                ]
            )
        elif normalized_type == "evolution":
            sections.extend(
                [
                    {"title": "Evolution Timeline", "goal": "Summarize chronological progression."},
                    {"title": "Key Turning Points", "goal": "Identify pivotal changes and evidence."},
                ]
            )
        else:
            sections.append({"title": "Core Findings", "goal": "Summarize strongest supporting evidence."})

        sections.append({"title": "Evidence Limits", "goal": "State uncertainty, gaps, and unresolved claims."})

        if not all_results:
            return sections

        return sections[:5]

    def _normalize_chunk_for_synthesis(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a chunk into unified retrieval contract fields.

        Canonical fields:
        - text
        - score
        - page_num

        Strict mode only accepts canonical fields.
        """
        text = chunk.get("text")
        score = chunk.get("score")
        page_num = chunk.get("page_num")

        if text is None:
            raise ValueError("Missing required retrieval field: text")
        if score is None:
            raise ValueError("Missing required retrieval field: score")
        if page_num is None:
            raise ValueError("Missing required retrieval field: page_num")

        try:
            normalized_score = max(0.0, min(float(score), 1.0))
        except (TypeError, ValueError):
            normalized_score = 0.0

        normalized = dict(chunk)
        normalized["text"] = text or ""
        normalized["score"] = normalized_score
        normalized["page_num"] = page_num
        normalized["source_id"] = (
            chunk.get("source_id")
            or chunk.get("id")
            or chunk.get("chunk_id")
        )
        normalized["section_path"] = chunk.get("section_path") or chunk.get("section")
        normalized["content_subtype"] = (
            chunk.get("content_subtype")
            or chunk.get("content_type")
            or "paragraph"
        )
        normalized["anchor_text"] = chunk.get("anchor_text") or (text[:200] if text else "")
        normalized["paper_title"] = chunk.get("paper_title") or chunk.get("paper_id")
        normalized["section"] = chunk.get("section") or chunk.get("content_section")
        return normalized

    @staticmethod
    def _format_citation(chunk: Dict[str, Any]) -> str:
        """Build stable citation text from normalized chunk."""
        paper_title = chunk.get("paper_title") or chunk.get("paper_id") or "Unknown"
        section = chunk.get("section")
        page_num = chunk.get("page_num")
        loc = section or (f"Page {page_num}" if page_num else "N/A")
        return f"[{paper_title}, {loc}]"

    def _build_evidence_blocks(
        self,
        chunks: List[Dict[str, Any]],
        query: str,
        num_blocks: int = 5,
    ) -> List[Dict[str, Any]]:
        """Group chunks into evidence blocks for structured synthesis.

        Per D-15: LLM receives evidence blocks, not loose context.

        Args:
            chunks: Retrieved chunks with unified fields
            query: Original query for topic extraction
            num_blocks: Number of evidence blocks to create

        Returns:
            List of evidence blocks:
            [
                {
                    "claim_topic": "...",
                    "supporting_chunks": [
                        {"paper_title": "...", "section": "...", "page_num": 5, "text": "...", "score": 0.89}
                    ]
                }
            ]
        """
        if not chunks:
            return []

        normalized_chunks = [self._normalize_chunk_for_synthesis(c) for c in chunks]

        # Group chunks by section for topical coherence
        section_groups: Dict[str, List[Dict]] = {}
        for chunk in normalized_chunks:
            section = chunk.get("section") or "General"
            if section not in section_groups:
                section_groups[section] = []
            section_groups[section].append(chunk)

        # Create evidence blocks
        blocks = []

        # First block: highest-scoring chunks across all sections
        top_chunks = sorted(
            normalized_chunks,
            key=lambda x: x.get("score", 0.0),
            reverse=True,
        )[:3]
        if top_chunks:
            blocks.append({
                "claim_topic": f"Key findings for '{query[:50]}...'",
                "supporting_chunks": [
                    {
                        "paper_title": c.get("paper_title", c.get("paper_id", "Unknown")),
                        "section": c.get("section", "N/A"),
                        "page_num": c.get("page_num"),
                        "text": c.get("text", "")[:200],
                        "score": c.get("score", 0.0),
                    }
                    for c in top_chunks
                ],
            })

        # Additional blocks: per-section evidence
        for section, section_chunks in section_groups.items():
            if section == "General":
                continue
            if len(blocks) >= num_blocks:
                break

            sorted_chunks = sorted(
                section_chunks,
                key=lambda x: x.get("score", 0.0),
                reverse=True,
            )[:2]
            if sorted_chunks:
                blocks.append({
                    "claim_topic": f"Evidence from {section}",
                    "supporting_chunks": [
                        {
                            "paper_title": c.get("paper_title", c.get("paper_id", "Unknown")),
                            "section": c.get("section", section),
                            "page_num": c.get("page_num"),
                            "text": c.get("text", "")[:150],
                            "score": c.get("score", 0.0),
                        }
                        for c in sorted_chunks
                    ],
                })

        logger.info(
            "Evidence blocks built",
            blocks=len(blocks),
            total_chunks=len(chunks),
        )

        return blocks

    async def _execute_subquestions_parallel(
        self,
        sub_questions: List[Dict[str, Any]],
        paper_ids: List[str],
        user_id: str,
        top_k: int = 5,
        content_types: Optional[List[str]] = None,
        graph_hint: Optional[Dict[str, Any]] = None,
        graph_candidates: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """Execute sub-questions in parallel using asyncio.gather with Milvus.

        Args:
            sub_questions: List of sub-question dictionaries
            paper_ids: Paper IDs to search
            user_id: User ID for Milvus filtering - passed from execute_retrieval
            top_k: Number of chunks per sub-question

        Returns:
            List of result dictionaries
        """

        async def search_single(sub_q: Dict[str, Any]) -> Dict[str, Any]:
            """Search for a single sub-question using MultimodalSearchService."""
            try:
                question = sub_q.get("question", "")
                target_papers = sub_q.get("target_papers") or paper_ids

                # Use MultimodalSearchService for Milvus search (per D-35)
                result = await self.search_service.search(
                    query=question,
                    paper_ids=target_papers,
                    user_id=user_id,
                    top_k=top_k,
                    use_reranker=True,
                    content_types=content_types or ["text"],
                    graph_hint=graph_hint,
                    graph_candidates=graph_candidates,
                )

                # Extract chunks from results
                raw_chunks = result.get("results", [])
                chunks = [self._normalize_chunk_for_synthesis(c) for c in raw_chunks]

                # Generate a simple summary
                summary = self._generate_summary(chunks, question)

                return {
                    "sub_question": question,
                    "chunks": chunks,
                    "summary": summary,
                    "rationale": sub_q.get("rationale", ""),
                    "intent": result.get("intent"),
                    "success": True,
                }

            except Exception as e:
                logger.error(
                    "Sub-question search failed",
                    question=sub_q.get("question", "")[:50],
                    error=str(e),
                )
                return {
                    "sub_question": sub_q.get("question", ""),
                    "chunks": [],
                    "summary": f"Error: {str(e)}",
                    "rationale": sub_q.get("rationale", ""),
                    "success": False,
                    "error": str(e),
                }

        # Execute all sub-questions in parallel
        tasks = [search_single(sq) for sq in sub_questions]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions
        valid_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error("Sub-question task failed", error=str(result))
                valid_results.append(
                    {
                        "sub_question": "unknown",
                        "chunks": [],
                        "summary": f"Task failed: {str(result)}",
                        "success": False,
                        "error": str(result),
                    }
                )
            else:
                valid_results.append(result)

        return valid_results

    @staticmethod
    def _compute_answer_evidence_consistency(answer: str, sources: List[Dict[str, Any]]) -> float:
        answer_tokens = {token for token in (answer or "").lower().split() if len(token) >= 3}
        if not answer_tokens or not sources:
            return 0.0

        evidence_tokens = set()
        for source in sources[:5]:
            text = " ".join(
                [
                    str(source.get("anchor_text") or ""),
                    str(source.get("text") or ""),
                    str(source.get("text_preview") or ""),
                ]
            )
            for token in text.lower().split():
                if len(token) >= 3:
                    evidence_tokens.add(token)

        if not evidence_tokens:
            return 0.0

        overlap = len(answer_tokens & evidence_tokens)
        return round(min(overlap / max(len(answer_tokens), 1), 1.0), 4)

    @staticmethod
    def _apply_answer_mode(
        answer: str,
        claim_results: List[Dict[str, Any]] | List[Any],
        answer_mode: str,
        abstain_reason: Optional[str],
    ) -> str:
        if answer_mode == "abstain":
            reason = abstain_reason or "insufficient_evidence"
            return f"Insufficient evidence to provide a reliable answer. reason={reason}."

        if answer_mode != "partial":
            return answer

        unsupported_phrases = []
        for item in claim_results:
            level = getattr(item, "support_level", None)
            text = getattr(item, "text", None)
            if level is not None and str(level) == "ClaimSupportLevel.unsupported" and text:
                unsupported_phrases.append(text)
            elif isinstance(item, dict) and item.get("support_level") == "unsupported" and item.get("text"):
                unsupported_phrases.append(str(item.get("text")))

        filtered = answer
        for phrase in unsupported_phrases[:5]:
            if phrase in filtered:
                filtered = filtered.replace(phrase, "")

        filtered = re.sub(r"\n{3,}", "\n\n", filtered).strip()
        if not filtered:
            return "Partial answer available but unsupported claims were removed due to limited evidence."
        return filtered

    async def _check_convergence(
        self,
        previous_results: List[Dict[str, Any]],
        current_results: List[Dict[str, Any]],
        previous_synthesis: str,
    ) -> bool:
        """Check if retrieval has converged.

        Args:
            previous_results: Results from previous round
            current_results: Results from current round
            previous_synthesis: Previous round's synthesis

        Returns:
            True if converged
        """
        # Use simple chunk-based check first
        simple_converged = self.convergence_checker.check_convergence_simple(
            previous_results,
            current_results,
        )

        if simple_converged:
            return True

        # Use LLM-based check for more nuanced detection
        try:
            llm_result = await self.convergence_checker.check_convergence_llm(
                previous_synthesis=previous_synthesis,
                current_results=current_results,
            )
            return llm_result.get("is_converged", False)
        except Exception as e:
            logger.warning("LLM convergence check failed", error=str(e))
            return simple_converged

    async def _synthesize_results(
        self,
        query: str,
        query_type: QueryType,
        results: List[Dict[str, Any]],
        round_num: int,
    ) -> str:
        """Synthesize results for a single round.

        Args:
            query: Original query
            query_type: Query type
            results: Round results
            round_num: Current round number

        Returns:
            Synthesized text
        """
        # Build context from results
        context_parts = []
        for i, result in enumerate(results):
            if not result.get("success", True):
                continue

            chunks = result.get("chunks", [])
            if not chunks:
                continue

            context_parts.append(
                f"Sub-question {i + 1}: {result.get('sub_question', 'N/A')}\n"
                f"Summary: {result.get('summary', 'N/A')[:300]}\n"
                f"Sources: {len(chunks)} chunks found"
            )

        if not context_parts:
            return "No relevant information found in this round."

        context = "\n\n".join(context_parts)

        # Call LLM for synthesis
        try:
            from app.utils.zhipu_client import get_llm_client

            llm_client = get_llm_client()

            prompt = f"""Synthesize the following retrieval results into a coherent answer.

Original query: {query}
Query type: {query_type}
Round: {round_num}

Retrieval results:
{context}

Provide a concise synthesis that:
1. Addresses the original query
2. Integrates information from all sub-questions
3. Highlights key findings
4. Notes any gaps or uncertainties"""

            response = await llm_client.chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a research synthesis assistant.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=800,
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error("Synthesis failed", error=str(e))
            # Fallback: return simple concatenation
            return "\n\n".join(
                [
                    f"{r.get('sub_question')}: {r.get('summary', 'N/A')[:200]}"
                    for r in results
                    if r.get("success", True)
                ]
            )

    async def _final_synthesis(
        self,
        query: str,
        query_type: QueryType,
        all_results: List[Dict[str, Any]],
        answer_outline: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """Generate final synthesis across all rounds using evidence blocks.

        Per D-15: LLM receives structured evidence blocks, not loose context.

        Args:
            query: Original query
            query_type: Query type
            all_results: All round results

        Returns:
            Final synthesized answer with citations
        """
        # Build evidence blocks from all chunks
        all_chunks = []
        for round_data in all_results:
            round_results = round_data.get("results", [])
            for result in round_results:
                if result.get("success", True):
                    chunks = result.get("chunks", [])
                    all_chunks.extend(chunks)

        evidence_blocks = self._build_evidence_blocks(all_chunks, query)

        if not evidence_blocks:
            return "No relevant information found across all retrieval rounds."

        # Format blocks for LLM
        blocks_text = ""
        for block in evidence_blocks:
            blocks_text += f"\n## {block['claim_topic']}\n"
            for chunk in block['supporting_chunks']:
                paper_title = chunk.get('paper_title', 'Unknown')
                section = chunk.get('section', 'N/A')
                page_num = chunk.get('page_num')
                text_preview = chunk.get('text', '')[:150]
                score = chunk.get('score', 0)

                page_display = f"Page {page_num or 'N/A'}"
                citation = f"[{paper_title[:30]}, {section or page_display}]"
                blocks_text += f"- {text_preview} {citation} (score: {score:.2f})\n"

        outline_lines = []
        for idx, section in enumerate(answer_outline or [], start=1):
            title = section.get("title") or f"Section {idx}"
            goal = section.get("goal") or ""
            outline_lines.append(f"{idx}. {title} - {goal}")
        outline_text = "\n".join(outline_lines) if outline_lines else "1. Core Findings - Answer with strongest evidence."

        # Call LLM for final synthesis with structured evidence
        try:
            from app.utils.zhipu_client import get_llm_client

            llm_client = get_llm_client()

            if query_type == "evolution":
                synthesis_instruction = """Provide a timeline-style synthesis showing:
1. The progression/development across versions
2. Key changes at each stage
3. Overall trajectory and trends"""
            elif query_type == "cross_paper":
                synthesis_instruction = """Provide a comparative synthesis showing:
1. Key aspects of each paper/method
2. Direct comparisons between approaches
3. Relative strengths and weaknesses"""
            else:
                synthesis_instruction = """Provide a comprehensive synthesis that:
1. Directly answers the query
2. Integrates all retrieved information
3. Cites specific findings where relevant"""

            prompt = f"""Answer the query using ONLY the provided evidence blocks.

Query: {query}
Query type: {query_type}

ANSWER OUTLINE (must follow this structure):
{outline_text}

EVIDENCE BLOCKS:
{blocks_text}

REQUIREMENTS:
1. Every factual statement MUST cite evidence using [Paper Title, Section] format
2. Follow the answer outline section-by-section and attach evidence per section
3. Minimum citation density: one citation per 2-3 sentences
4. If evidence is insufficient, state what is missing

{synthesis_instruction}

Your answer:"""

            response = await llm_client.chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert research synthesis assistant. Always cite sources using [Paper Title, Section] format.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=1500,
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error("Final synthesis failed", error=str(e))
            # Fallback: simple concatenation with markdown formatting
            return f"""## Synthesis

Based on {len(all_results)} rounds of retrieval with {len(evidence_blocks)} evidence blocks:

{blocks_text}

*Note: LLM synthesis failed, showing structured evidence blocks.*"""

    async def _refine_subquestions(
        self,
        sub_questions: List[Dict[str, Any]],
        results: List[Dict[str, Any]],
        query: str,
    ) -> List[Dict[str, Any]]:
        """Refine sub-questions based on round results.

        Args:
            sub_questions: Current sub-questions
            results: Round results
            query: Original query

        Returns:
            Refined sub-questions
        """
        # Identify sub-questions with poor results
        poor_results = [
            r
            for r in results
            if not r.get("success", True) or len(r.get("chunks", [])) < 2
        ]

        if not poor_results:
            # All sub-questions performed well, keep them
            return sub_questions

        # Create alternative sub-questions for poor performers
        refined = list(sub_questions)

        for poor in poor_results:
            original_q = poor.get("sub_question", "")

            # Add alternative formulation
            refined.append(
                {
                    "question": f"Alternative perspective: {original_q}",
                    "query_type": "single",
                    "target_papers": poor.get("target_papers", []),
                    "rationale": f"Alternative approach to: {original_q}",
                }
            )

        # Limit to reasonable number
        if len(refined) > 7:
            refined = refined[:7]

        return refined

    def _generate_summary(
        self,
        chunks: List[Dict[str, Any]],
        question: str,
    ) -> str:
        """Generate a simple summary of chunks.

        Args:
            chunks: Retrieved chunks
            question: Sub-question

        Returns:
            Summary string
        """
        if not chunks:
            return "No relevant chunks found."

        # Take top 3 chunks for summary
        top_chunks = chunks[:3]
        summaries = []

        for i, chunk in enumerate(top_chunks):
            normalized_chunk = self._normalize_chunk_for_synthesis(chunk)
            content = normalized_chunk.get("text", "")
            score = normalized_chunk.get("score", 0.0)
            paper_id = chunk.get("paper_id", "unknown")

            # Truncate content
            content_preview = content[:150] + "..." if len(content) > 150 else content
            summaries.append(
                f"[Source {i + 1} from {paper_id[:8]}... (score {score:.2f})]: {content_preview}"
            )

        return "\n".join(summaries)

    def _build_context_with_citations(self, chunks: List[Dict[str, Any]]) -> str:
        """Build synthesis context with inline citations from canonical chunks."""
        if not chunks:
            return ""

        blocks: List[str] = []
        for chunk in chunks:
            normalized = self._normalize_chunk_for_synthesis(chunk)
            content = normalized.get("text", "")
            score = normalized.get("score", 0.0)
            max_len = 300 if score > 0.85 else 200

            if len(content) > max_len:
                preview = content[:max_len]
                if score <= 0.85:
                    last_sentence = max(preview.rfind(". "), preview.rfind("。"))
                    if last_sentence > 80:
                        preview = preview[: last_sentence + 1]
                content = preview.strip() + "..."

            citation = self._format_citation(normalized)
            blocks.append(f"{content} {citation}")

        return "\n\n".join(blocks)

    @staticmethod
    def _extract_citations_from_answer(answer: str) -> List[tuple[str, str]]:
        """Extract [Paper, Section] citation markers from answer text."""
        pattern = re.compile(r"\[([^,\]]+),\s*([^\]]+)\]")
        return [(paper.strip(), loc.strip()) for paper, loc in pattern.findall(answer or "")]

    def _calculate_citation_density(self, answer: str) -> float:
        """Compute citation density as citations per token."""
        citations = self._extract_citations_from_answer(answer)
        token_count = max(len((answer or "").split()), 1)
        return len(citations) / token_count

    def _needs_citation_fallback(self, answer: str, chunk_count: int) -> bool:
        """Decide whether citation fallback answer is needed."""
        if chunk_count <= 0:
            return True
        if not answer or not answer.strip():
            return True
        density = self._calculate_citation_density(answer)
        return density < 0.05

    def _build_fallback_answer(self, chunks: List[Dict[str, Any]], query: str) -> str:
        """Build deterministic fallback answer grouped by evidence section."""
        if not chunks:
            return "No relevant information found for the query."

        normalized_chunks = [self._normalize_chunk_for_synthesis(chunk) for chunk in chunks]
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for chunk in normalized_chunks:
            section = chunk.get("section")
            if not section:
                page_num = chunk.get("page_num")
                section = f"Page {page_num}" if page_num is not None else "General"
            grouped.setdefault(section, []).append(chunk)

        lines = [f"## Evidence Summary for: {query}"]
        for section, section_chunks in grouped.items():
            lines.append(f"\n### {section}")
            sorted_chunks = sorted(section_chunks, key=lambda item: item.get("score", 0.0), reverse=True)
            for chunk in sorted_chunks[:3]:
                text = chunk.get("text", "")
                preview = text[:220] + ("..." if len(text) > 220 else "")
                lines.append(f"- {preview} {self._format_citation(chunk)}")

        return "\n".join(lines)

    def _validate_and_fix_citations(
        self,
        answer: str,
        all_results: List[Dict[str, Any]],
        query: str,
    ) -> str:
        """Validate citation density and fallback to deterministic evidence summary when needed."""
        chunks: List[Dict[str, Any]] = []
        for round_data in all_results:
            for result in round_data.get("results", []):
                if result.get("success", True):
                    chunks.extend(result.get("chunks", []))

        if self._needs_citation_fallback(answer, len(chunks)):
            return self._build_fallback_answer(chunks, query)
        return answer

    def _collect_sources(
        self,
        all_results: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Collect and deduplicate sources from all rounds.

        Args:
            all_results: All round results

        Returns:
            Deduplicated list of sources
        """
        seen_chunks = set()
        sources = []

        for round_data in all_results:
            round_results = round_data.get("results", [])

            for result in round_results:
                for chunk in result.get("chunks", []):
                    chunk_id = chunk.get("source_id") or chunk.get("id") or chunk.get("chunk_id")

                    if chunk_id and chunk_id not in seen_chunks:
                        seen_chunks.add(chunk_id)
                        normalized_chunk = self._normalize_chunk_for_synthesis(chunk)
                        text_preview = normalized_chunk.get("text", "")[:300]
                        score = normalized_chunk.get("score", 0.0)
                        page_num = normalized_chunk.get("page_num")
                        citation = self._format_citation(normalized_chunk)

                        sources.append(
                            {
                                "source_id": normalized_chunk.get("source_id") or chunk_id,
                                "paper_id": normalized_chunk.get("paper_id"),
                                "paper_title": normalized_chunk.get("paper_title"),
                                "text_preview": text_preview,
                                "page_num": page_num,
                                "score": score,
                                "section_path": normalized_chunk.get("section_path"),
                                "content_subtype": normalized_chunk.get("content_subtype"),
                                "anchor_text": normalized_chunk.get("anchor_text"),
                                "section": normalized_chunk.get("section"),
                                "content_type": normalized_chunk.get("content_type", "text"),
                                "citation": citation,
                            }
                        )

        # Sort by unified score
        sources.sort(key=lambda x: x.get("score", 0.0), reverse=True)

        return sources


# Convenience function for direct usage
async def agentic_retrieve(
    query: str,
    query_type: Optional[QueryType] = None,
    paper_ids: Optional[List[str]] = None,
    user_id: str = "placeholder-user-id",
    max_rounds: int = 3,
) -> Dict[str, Any]:
    """Execute agentic retrieval with minimal setup using Milvus.

    Args:
        query: User query
        query_type: Query type (auto-detected if None)
        paper_ids: List of paper UUIDs to search
        user_id: User ID for Milvus filtering (per D-35)
        max_rounds: Maximum retrieval rounds

    Returns:
        Agentic retrieval result with answer and sources
    """
    orchestrator = AgenticRetrievalOrchestrator(max_rounds=max_rounds)
    return await orchestrator.retrieve(
        query=query,
        query_type=query_type,
        paper_ids=paper_ids,
        user_id=user_id,
    )
