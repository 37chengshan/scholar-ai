"""Agentic retrieval orchestrator for complex cross-paper queries.

Implements multi-round retrieval with:
- Query decomposition into sub-questions
- Parallel sub-question execution via asyncio.gather
- LLM synthesis of results
- Convergence detection (max 3 rounds or early convergence)
- Citation enforcement with post-processing validation and fallback

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
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

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
        """Generate final synthesis across all rounds with citation enforcement.

        Args:
            query: Original query
            query_type: Query type
            all_results: All round results

        Returns:
            Final synthesized answer with validated citations
        """
        # Collect all chunks for citation context
        all_chunks = []
        for round_data in all_results:
            round_results = round_data.get("results", [])
            for result in round_results:
                if not result.get("success", True):
                    continue
                chunks = result.get("chunks", [])
                all_chunks.extend(chunks)

        if not all_chunks:
            return "No relevant information found across all retrieval rounds."

        # Build context with citations using helper method
        full_context = self._build_context_with_citations(all_chunks)

        # Call LLM for final synthesis with citation enforcement
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

            # Citation enforcement prompt
            citation_instruction = """
CRITICAL CITATION REQUIREMENTS:
- EVERY factual statement MUST include a citation in [Paper Title, Section] format
- Use the exact citation markers provided in the context above
- Minimum citation density: at least one citation per 2-3 sentences
- Example format: "YOLOv1 introduced unified detection [YOLOv1 Paper, Introduction]."

FORMAT YOUR RESPONSE:
- Use ## headers for main sections
- Use - bullet points for lists
- Each bullet point must end with a citation"""

            prompt = f"""Generate a final synthesized answer based on the retrieved information.

Original query: {query}
Query type: {query_type}

Retrieved information (each item includes a citation marker):
{full_context}

{synthesis_instruction}

{citation_instruction}

Your answer MUST include citations from the provided context. Do not make claims without citations."""

            response = await llm_client.chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert research synthesis assistant. You ALWAYS cite your sources using [Paper Title, Section] format.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=1500,
            )

            raw_answer = response.choices[0].message.content

            # Validate and fix citations if needed
            validated_answer = self._validate_and_fix_citations(
                answer=raw_answer,
                all_results=all_results,
                query=query,
            )

            return validated_answer

        except Exception as e:
            logger.error("Final synthesis failed", error=str(e))
            # Fallback: use structured fallback answer
            return self._build_fallback_answer(all_chunks, query)

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
            content = chunk.get("content", "")
            similarity = chunk.get("similarity", 0)
            paper_id = chunk.get("paper_id", "unknown")

            # Truncate content
            content_preview = content[:150] + "..." if len(content) > 150 else content
            summaries.append(
                f"[Source {i + 1} from {paper_id[:8]}... (score {similarity:.2f})]: {content_preview}"
            )

        return "\n".join(summaries)

    def _build_context_with_citations(
        self,
        chunks: List[Dict[str, Any]],
    ) -> str:
        """Build formatted context string with citation markers.

        Args:
            chunks: List of chunks with paper_title, section, page, content, similarity

        Returns:
            Formatted context string with [Paper Title, Section] citation markers

        Citation format:
            - [paper_title, section] when section available
            - [paper_title, Page {page}] when section missing
            - [paper_id, section/page] when paper_title missing

        Truncation strategy:
            - High similarity (>0.85): extend to 300 chars
            - Normal similarity: truncate to 200 chars at sentence boundary
        """
        if not chunks:
            return ""

        context_parts = []

        for chunk in chunks:
            content = chunk.get("content", "")
            similarity = chunk.get("similarity", 0)

            # Build citation marker
            citation = self._build_citation(chunk)

            # Truncate content based on similarity threshold
            high_similarity_threshold = 0.85
            if similarity > high_similarity_threshold:
                max_length = 300
            else:
                max_length = 200

            truncated = self._truncate_at_sentence_boundary(content, max_length)

            # Format chunk with citation
            context_parts.append(f"{truncated} {citation}")

        return "\n".join(context_parts)

    def _truncate_at_sentence_boundary(
        self,
        content: str,
        max_length: int,
    ) -> str:
        """Truncate content at sentence boundary.

        Args:
            content: Full content string
            max_length: Maximum desired length

        Returns:
            Truncated content ending at sentence boundary (or max_length if no boundary)
        """
        if len(content) <= max_length:
            return content

        # Look for sentence boundary near the end of max_length range
        # Prefer boundary in the last 50 chars of the range
        truncated = content[:max_length]

        # Look for sentence endings (. ! ?) in the last portion
        search_range_start = max(max_length - 100, max_length // 2)
        search_portion = truncated[search_range_start:]

        sentence_enders = [".", "!", "?"]
        last_boundary = -1

        for ender in sentence_enders:
            pos = search_portion.rfind(ender)  # Use rfind for last occurrence
            if pos != -1:
                # Adjust position to full truncated string
                full_pos = search_range_start + pos
                if full_pos > last_boundary:
                    last_boundary = full_pos

        # If found a boundary in search range, truncate there
        if last_boundary > search_range_start:
            return truncated[:last_boundary + 1]

        # No good boundary found near end, use max_length with ellipsis
        return truncated + "..."

    def _build_citation(self, chunk: Dict[str, Any]) -> str:
        """Build citation string for a single chunk.

        Args:
            chunk: Chunk dict with paper_title, paper_id, section, page

        Returns:
            Citation string like "[Paper Title, Section]" or "[Paper Title, Page 5]"
        """
        paper_title = chunk.get("paper_title") or chunk.get("paper_id", "Unknown")
        section = chunk.get("section")

        if section:
            return f"[{paper_title}, {section}]"
        else:
            page = chunk.get("page")
            return f"[{paper_title}, Page {page}]" if page else f"[{paper_title}]"

    # ============================================================
    # Citation Validation and Fallback Methods
    # ============================================================

    def _extract_citations_from_answer(
        self,
        answer: str,
    ) -> List[Tuple[str, str]]:
        """Extract [Paper Title, Section] citation markers from answer text.

        Args:
            answer: Generated answer text

        Returns:
            List of (paper_title, section) tuples extracted from citations
        """
        # Pattern: [Paper Title, Section] or [Paper Title, Page N]
        pattern = r"\[([^,\[\]]+),\s*([^\[\]]+)\]"
        matches = re.findall(pattern, answer)

        citations = []
        for paper, location in matches:
            # Clean up extracted values
            paper = paper.strip()
            location = location.strip()
            if paper and location:
                citations.append((paper, location))

        return citations

    def _calculate_citation_density(
        self,
        answer: str,
    ) -> float:
        """Calculate citation density (citations per content length).

        Args:
            answer: Generated answer text

        Returns:
            Citation density ratio (higher = more citations)
        """
        citations = self._extract_citations_from_answer(answer)
        citation_count = len(citations)

        # Count meaningful content (excluding citation markers themselves)
        # Remove citation markers to get pure content
        content_only = re.sub(r"\[([^,\[\]]+),\s*([^\[\]]+)\]", "", answer)
        content_only = content_only.strip()

        # Calculate word count of content
        word_count = len(content_only.split())

        if word_count == 0:
            return 0.0

        # Density = citations per 100 words
        density = (citation_count / word_count) * 100

        return density

    def _needs_citation_fallback(
        self,
        answer: str,
        chunk_count: int,
    ) -> bool:
        """Determine if fallback answer is needed due to insufficient citations.

        Args:
            answer: Generated answer text
            chunk_count: Number of chunks available for citation

        Returns:
            True if fallback answer should be used
        """
        citations = self._extract_citations_from_answer(answer)
        citation_count = len(citations)

        # Threshold: need at least 0.5 citations per chunk (minimum density)
        # Example: 4 chunks -> need at least 2 citations
        min_citations = max(1, int(chunk_count * 0.5))

        # Also check density threshold (should have ~2 citations per 100 words)
        density = self._calculate_citation_density(answer)

        # Fallback needed if:
        # 1. Citation count is below chunk-based threshold
        # 2. OR density is very low (< 1 citation per 100 words)
        needs_fallback = citation_count < min_citations or density < 1.0

        logger.debug(
            "Citation fallback check",
            citation_count=citation_count,
            min_citations=min_citations,
            density=density,
            needs_fallback=needs_fallback,
        )

        return needs_fallback

    def _validate_and_fix_citations(
        self,
        answer: str,
        all_results: List[Dict[str, Any]],
        query: str,
    ) -> str:
        """Validate citations in answer and fix if insufficient.

        Args:
            answer: Generated answer text
            all_results: All round results with chunks
            query: Original user query

        Returns:
            Either original answer (if citations sufficient) or fallback answer
        """
        # Collect all chunks from results
        all_chunks = []
        for round_data in all_results:
            round_results = round_data.get("results", [])
            for result in round_results:
                if not result.get("success", True):
                    continue
                chunks = result.get("chunks", [])
                all_chunks.extend(chunks)

        chunk_count = len(all_chunks)

        # Check if fallback needed
        if not self._needs_citation_fallback(answer, chunk_count):
            logger.info(
                "Citations sufficient, keeping original answer",
                chunk_count=chunk_count,
            )
            return answer

        # Generate fallback answer with proper citations
        logger.warning(
            "Insufficient citations, generating fallback answer",
            chunk_count=chunk_count,
            query=query[:50],
        )

        return self._build_fallback_answer(all_chunks, query)

    def _build_fallback_answer(
        self,
        chunks: List[Dict[str, Any]],
        query: str,
    ) -> str:
        """Build structured fallback answer with guaranteed citations.

        Args:
            chunks: All available chunks
            query: Original user query

        Returns:
            Structured answer with proper [Paper, Section] citations for each item
        """
        if not chunks:
            return "No relevant information found for your query."

        # Group chunks by section
        section_groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for chunk in chunks:
            section = chunk.get("section") or "General"
            section_groups[section].append(chunk)

        # Build structured answer
        answer_parts = []
        answer_parts.append(f"## Answer to: {query}")
        answer_parts.append("")
        answer_parts.append("Based on the retrieved sources:")
        answer_parts.append("")

        # For each section, add header and bullet items with citations
        for section, section_chunks in section_groups.items():
            # Add section header
            answer_parts.append(f"### {section}")
            answer_parts.append("")

            # Sort by similarity (highest first)
            sorted_chunks = sorted(
                section_chunks,
                key=lambda x: x.get("similarity", 0),
                reverse=True,
            )

            # Add bullet points with citations
            for chunk in sorted_chunks:
                content = chunk.get("content", "")
                citation = self._build_citation(chunk)

                # Truncate content to ~150 chars for readability
                truncated = self._truncate_at_sentence_boundary(content, 150)

                answer_parts.append(f"- {truncated} {citation}")

            answer_parts.append("")

        # Add summary footer
        answer_parts.append("---")
        answer_parts.append(f"*Sources: {len(chunks)} chunks from {len(section_groups)} sections*")

        return "\n".join(answer_parts)

    def _collect_sources(
        self,
        all_results: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Collect and deduplicate sources from all rounds with citations.

        Args:
            all_results: All round results

        Returns:
            Deduplicated list of sources with citation field
        """
        seen_chunks = set()
        sources = []

        for round_data in all_results:
            round_results = round_data.get("results", [])

            for result in round_results:
                # Skip failed results
                if not result.get("success", True):
                    continue

                for chunk in result.get("chunks", []):
                    chunk_id = chunk.get("id") or chunk.get("chunk_id")

                    if chunk_id and chunk_id not in seen_chunks:
                        seen_chunks.add(chunk_id)

                        # Build citation for this chunk
                        citation = self._build_citation(chunk)

                        sources.append(
                            {
                                "chunk_id": chunk_id,
                                "paper_id": chunk.get("paper_id"),
                                "paper_title": chunk.get("paper_title"),
                                "content_preview": chunk.get("content", "")[:300],
                                "page": chunk.get("page"),
                                "similarity": chunk.get("similarity"),
                                "section": chunk.get("section"),
                                "citation": citation,
                            }
                        )

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
