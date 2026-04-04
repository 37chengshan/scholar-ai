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

    async def retrieve(
        self,
        query: str,
        query_type: Optional[QueryType] = None,
        paper_ids: Optional[List[str]] = None,
        user_id: str = "placeholder-user-id",
        top_k_per_subquestion: int = 5,
    ) -> Dict[str, Any]:
        """Execute agentic retrieval with multi-round support.

        Args:
            query: Original user query
            query_type: Query type (auto-detected if None)
            paper_ids: List of paper IDs to search
            user_id: User ID for Milvus filtering (per D-35)
            top_k_per_subquestion: Number of chunks per sub-question

        Returns:
            Dictionary with synthesized answer, sub-questions, sources, and metadata
        """
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

            all_results.append({
                "round": round_num,
                "results": round_results,
            })

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
            if query_type in ("evolution", "cross_paper") and round_num < self.max_rounds:
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

        logger.info(
            "Agentic retrieval completed",
            query=query[:50],
            rounds=rounds_executed,
            converged=converged,
            sources=len(all_sources),
        )

        return {
            "answer": final_answer,
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
            },
        }

    async def _execute_subquestions_parallel(
        self,
        sub_questions: List[Dict[str, Any]],
        paper_ids: List[str],
        user_id: str = "placeholder-user-id",
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Execute sub-questions in parallel using asyncio.gather with Milvus.

        Args:
            sub_questions: List of sub-question dictionaries
            paper_ids: Paper IDs to search
            user_id: User ID for Milvus filtering (per D-35)
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
                chunks = result.get("results", [])

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
                valid_results.append({
                    "sub_question": "unknown",
                    "chunks": [],
                    "summary": f"Task failed: {str(result)}",
                    "success": False,
                    "error": str(result),
                })
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
                f"Sub-question {i+1}: {result.get('sub_question', 'N/A')}\n"
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
                    {"role": "system", "content": "You are a research synthesis assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=800
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error("Synthesis failed", error=str(e))
            # Fallback: return simple concatenation
            return "\n\n".join([
                f"{r.get('sub_question')}: {r.get('summary', 'N/A')[:200]}"
                for r in results if r.get('success', True)
            ])

    async def _final_synthesis(
        self,
        query: str,
        query_type: QueryType,
        all_results: List[Dict[str, Any]],
    ) -> str:
        """Generate final synthesis across all rounds.

        Args:
            query: Original query
            query_type: Query type
            all_results: All round results

        Returns:
            Final synthesized answer
        """
        # Combine all round results
        combined_context = []
        for round_data in all_results:
            round_num = round_data.get("round", 0)
            round_results = round_data.get("results", [])

            round_context = []
            for result in round_results:
                if not result.get("success", True):
                    continue
                chunks = result.get("chunks", [])
                if chunks:
                    round_context.append(
                        f"- {result.get('sub_question', 'N/A')}: "
                        f"{result.get('summary', 'N/A')[:200]}"
                    )

            if round_context:
                combined_context.append(
                    f"Round {round_num}:\n" + "\n".join(round_context)
                )

        if not combined_context:
            return "No relevant information found across all retrieval rounds."

        full_context = "\n\n".join(combined_context)

        # Call LLM for final synthesis
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

            prompt = f"""Generate a final synthesized answer based on all retrieval rounds.

Original query: {query}
Query type: {query_type}

Retrieved information across {len(all_results)} rounds:
{full_context}

{synthesis_instruction}

Format your response with clear sections and bullet points where appropriate."""

            response = await llm_client.chat_completion(
                messages=[
                    {"role": "system", "content": "You are an expert research synthesis assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1500
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error("Final synthesis failed", error=str(e))
            # Fallback: simple concatenation with markdown formatting
            return f"""## Synthesis

Based on {len(all_results)} rounds of retrieval:

{full_context}

*Note: LLM synthesis failed, showing raw retrieved information.*
"""

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
            r for r in results
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
            refined.append({
                "question": f"Alternative perspective: {original_q}",
                "query_type": "single",
                "target_papers": poor.get("target_papers", []),
                "rationale": f"Alternative approach to: {original_q}",
            })

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
            content = chunk.get("content", "")
            similarity = chunk.get("similarity", 0)
            paper_id = chunk.get("paper_id", "unknown")

            # Truncate content
            content_preview = content[:150] + "..." if len(content) > 150 else content
            summaries.append(
                f"[Source {i+1} from {paper_id[:8]}... (score {similarity:.2f})]: {content_preview}"
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
                        sources.append({
                            "chunk_id": chunk_id,
                            "paper_id": chunk.get("paper_id"),
                            "content_preview": chunk.get("content", "")[:300],
                            "page": chunk.get("page"),
                            "similarity": chunk.get("similarity"),
                            "section": chunk.get("section"),
                        })

        # Sort by similarity
        sources.sort(key=lambda x: x.get("similarity", 0), reverse=True)

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
