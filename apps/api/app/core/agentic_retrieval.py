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
from typing import Any, Dict, List, Optional

from app.utils.logger import logger
from app.core.query_decomposer import (
    QueryDecomposer,
    ConvergenceChecker,
    QueryType,
)
from app.core.multimodal_search_service import get_multimodal_search_service
from app.core.citation_verifier import get_citation_verifier


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

        sub_questions = await self.decomposer.decompose_query(
            query=query,
            query_type=query_type,
            paper_ids=paper_ids,
        )

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
            )

            all_results.append(
                {
                    "round": round_num,
                    "results": round_results,
                }
            )

            rounds_executed = round_num

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
                query_type=query_type or "single",
                results=round_results,
                round_num=round_num,
            )

            # If we've reached max rounds, don't continue
            if round_num >= self.max_rounds:
                break

            # For evolution/cross_paper queries, refine sub-questions based on results
            if (
                query_type in ("evolution", "cross_paper")
                and round_num < self.max_rounds
            ):
                sub_questions = await self._refine_subquestions(
                    sub_questions=sub_questions,
                    results=round_results,
                    query=query,
                )

        # Step 3: Final synthesis
        final_answer = await self._final_synthesis(
            query=query,
            query_type=query_type or "single",
            all_results=all_results,
        )

        # Collect all sources
        all_sources = self._collect_sources(all_results)

        verified_answer, verification_report = (
            self.citation_verifier.prune_unsupported_claims(final_answer, all_sources)
        )

        logger.info(
            "Agentic retrieval completed",
            query=query[:50],
            rounds=rounds_executed,
            converged=converged,
            sources=len(all_sources),
            citation_support=verification_report.get("support_score"),
        )

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
                "query_type": query_type or "single",
                "paper_count": len(paper_ids) if paper_ids else 0,
                "subquestion_count": len(sub_questions) if sub_questions else 0,
                "citation_verification": verification_report,
            },
        }

    def _normalize_chunk_for_synthesis(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a chunk into unified retrieval contract fields.

        Canonical fields:
        - text
        - score
        - page_num

        Legacy fields are read only for compatibility at this boundary.
        """
        text = chunk.get("text")
        score = chunk.get("score")
        page_num = chunk.get("page_num")
        used_legacy_fields = False

        if text is None:
            text = chunk.get("content_data")
            if text is None:
                text = chunk.get("content", "")
            used_legacy_fields = True

        if score is None:
            if chunk.get("similarity") is not None:
                score = chunk.get("similarity")
            elif chunk.get("distance") is not None:
                score = 1 - float(chunk.get("distance", 0.5))
            else:
                score = 0.0
            used_legacy_fields = True

        if page_num is None and chunk.get("page") is not None:
            page_num = chunk.get("page")
            used_legacy_fields = True

        if used_legacy_fields:
            logger.debug(
                "Legacy retrieval fields normalized at boundary",
                paper_id=chunk.get("paper_id"),
            )

        try:
            normalized_score = max(0.0, min(float(score), 1.0))
        except (TypeError, ValueError):
            normalized_score = 0.0

        normalized = dict(chunk)
        normalized["text"] = text or ""
        normalized["score"] = normalized_score
        normalized["page_num"] = page_num
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
                    content_types=["text"],  # Text-only for sub-questions
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

EVIDENCE BLOCKS:
{blocks_text}

REQUIREMENTS:
1. Every factual statement MUST cite evidence using [Paper Title, Section] format
2. Use evidence blocks - each block is a coherent claim with supporting sources
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
                    chunk_id = chunk.get("id") or chunk.get("chunk_id")

                    if chunk_id and chunk_id not in seen_chunks:
                        seen_chunks.add(chunk_id)
                        normalized_chunk = self._normalize_chunk_for_synthesis(chunk)
                        text_preview = normalized_chunk.get("text", "")[:300]
                        score = normalized_chunk.get("score", 0.0)
                        page_num = normalized_chunk.get("page_num")
                        citation = self._format_citation(normalized_chunk)

                        sources.append(
                            {
                                "chunk_id": chunk_id,
                                "paper_id": normalized_chunk.get("paper_id"),
                                "paper_title": normalized_chunk.get("paper_title"),
                                "text_preview": text_preview,
                                "page_num": page_num,
                                "score": score,
                                "section": normalized_chunk.get("section"),
                                "content_type": normalized_chunk.get("content_type", "text"),
                                "citation": citation,
                                # Backward-compatible aliases for legacy consumers.
                                "content_preview": text_preview,
                                "page": page_num,
                                "similarity": score,
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
