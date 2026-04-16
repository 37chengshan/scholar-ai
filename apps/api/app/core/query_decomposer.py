"""Query decomposition service for complex RAG queries.

Uses LiteLLM to decompose complex queries (evolution, cross-paper) into
3-5 sub-questions that can be executed in parallel.

Query types:
- single: Direct query on one paper
- cross_paper: Compare/contrast multiple papers
- evolution: Track changes across paper versions
"""

import json
import re
from typing import Any, Dict, List, Literal, Optional

from app.utils.logger import logger

# Query type classification
QueryType = Literal["single", "cross_paper", "evolution"]

# Keywords for query type detection
EVOLUTION_KEYWORDS = [
    "evolution", "timeline", "progress", "development",
    "history", "versions", "from v", "v1", "v2", "v3", "v4",
    "generations", "iterations", "improvements over time"
]

CROSS_PAPER_KEYWORDS = [
    "compare", "contrast", "difference", "similarities",
    "vs", "versus", "between", "among", "across papers"
]


class QueryDecomposer:
    """Decomposes complex queries into sub-questions using LLM.

    Attributes:
        max_subquestions: Maximum number of sub-questions (default: 5)
        min_subquestions: Minimum number of sub-questions (default: 3)
    """

    def __init__(
        self,
        max_subquestions: int = 5,
        min_subquestions: int = 3,
    ):
        """Initialize query decomposer.

        Args:
            max_subquestions: Maximum sub-questions to generate
            min_subquestions: Minimum sub-questions to generate
        """
        self.max_subquestions = max_subquestions
        self.min_subquestions = min_subquestions

    def classify_query(self, query: str) -> QueryType:
        """Classify query type based on content.

        Args:
            query: User query string

        Returns:
            Query type: single, cross_paper, or evolution
        """
        query_lower = query.lower()

        # Check for evolution keywords
        if any(kw in query_lower for kw in EVOLUTION_KEYWORDS):
            return "evolution"

        # Check for cross-paper keywords
        if any(kw in query_lower for kw in CROSS_PAPER_KEYWORDS):
            return "cross_paper"

        return "single"

    async def decompose_query(
        self,
        query: str,
        query_type: Optional[QueryType] = None,
        paper_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Decompose query into sub-questions using LLM.

        Args:
            query: Original user query
            query_type: Type of query (auto-detected if not provided)
            paper_ids: List of paper IDs available for search

        Returns:
            List of sub-question dictionaries
        """
        # Auto-detect query type if not provided
        if query_type is None:
            query_type = self.classify_query(query)

        # Single queries don't need decomposition
        if query_type == "single":
            return [{
                "question": query,
                "query_type": "single",
                "target_papers": paper_ids or [],
                "rationale": "Direct single-paper query"
            }]

        # Generate decomposition prompt
        prompt = self._build_decomposition_prompt(
            query=query,
            query_type=query_type,
            paper_ids=paper_ids or [],
        )

        try:
            # Call LLM via LiteLLM
            response = await self._call_llm(prompt)

            # Parse sub-questions from response
            sub_questions = self.parse_sub_questions(response)

            # Limit to max_subquestions
            if len(sub_questions) > self.max_subquestions:
                sub_questions = sub_questions[:self.max_subquestions]
                logger.info(
                    "Limited sub-questions to max",
                    max=self.max_subquestions,
                    total=len(sub_questions),
                )

            # Ensure minimum count by expanding if needed
            if len(sub_questions) < self.min_subquestions and query_type != "single":
                sub_questions = self._expand_subquestions(
                    sub_questions, query, query_type, paper_ids
                )

            logger.info(
                "Query decomposed",
                query=query[:50],
                query_type=query_type,
                subquestion_count=len(sub_questions),
            )

            return sub_questions

        except Exception as e:
            logger.error("Query decomposition failed", error=str(e), query=query[:50])
            # Fallback: return original query as single sub-question
            return [{
                "question": query,
                "query_type": query_type,
                "target_papers": paper_ids or [],
                "rationale": f"Fallback: decomposition failed - {str(e)}"
            }]

    def _build_decomposition_prompt(
        self,
        query: str,
        query_type: QueryType,
        paper_ids: List[str],
    ) -> str:
        """Build prompt for LLM query decomposition.

        Args:
            query: User query
            query_type: Type of query
            paper_ids: Available paper IDs

        Returns:
            Formatted prompt string
        """
        paper_context = f"\nAvailable papers: {', '.join(paper_ids)}" if paper_ids else ""

        if query_type == "evolution":
            template = f"""You are an expert research assistant. Decompose the following evolution/timeline query into {self.min_subquestions}-{self.max_subquestions} specific sub-questions.

Original query: "{query}"{paper_context}

For evolution queries, create sub-questions that:
1. Identify each version/generation mentioned
2. Ask about key features/improvements for each version
3. Compare consecutive versions
4. Ask about the overall progression pattern

Respond ONLY with a JSON array in this exact format:
[
  {{
    "question": "Specific sub-question text",
    "query_type": "single",
    "target_papers": ["paper_id_1"],
    "rationale": "Why this sub-question is relevant"
  }}
]

Requirements:
- Generate {self.min_subquestions}-{self.max_subquestions} sub-questions
- Each question should be self-contained and answerable
- Target papers should be from the available list when possible
- Include rationale for each sub-question"""

        elif query_type == "cross_paper":
            template = f"""You are an expert research assistant. Decompose the following cross-paper comparison query into {self.min_subquestions}-{self.max_subquestions} specific sub-questions.

Original query: "{query}"{paper_context}

For cross-paper queries, create sub-questions that:
1. Ask about key aspects of each individual paper
2. Identify points of comparison
3. Ask about differences and similarities
4. Request synthesis of the comparison

Respond ONLY with a JSON array in this exact format:
[
  {{
    "question": "Specific sub-question text",
    "query_type": "single",
    "target_papers": ["paper_id_1"],
    "rationale": "Why this sub-question is relevant"
  }}
]

Requirements:
- Generate {self.min_subquestions}-{self.max_subquestions} sub-questions
- Each question should be self-contained and answerable
- Target papers should be from the available list when possible
- Include rationale for each sub-question"""

        else:
            template = f"""You are an expert research assistant. Break down the following query into {self.min_subquestions}-{self.max_subquestions} sub-questions.

Original query: "{query}"{paper_context}

Respond ONLY with a JSON array in this exact format:
[
  {{
    "question": "Specific sub-question text",
    "query_type": "single",
    "target_papers": ["paper_id_1"],
    "rationale": "Why this sub-question is relevant"
  }}
]

Requirements:
- Generate {self.min_subquestions}-{self.max_subquestions} sub-questions
- Each question should be self-contained and answerable
- Target papers should be from the available list when possible
- Include rationale for each sub-question"""

        return template

    async def _call_llm(self, prompt: str) -> str:
        """Call ZhipuAI for query decomposition.

        Args:
            prompt: Decomposition prompt

        Returns:
            LLM response text
        """
        try:
            from app.utils.zhipu_client import get_llm_client
            
            llm_client = get_llm_client()
            
            response = await llm_client.chat_completion(
                messages=[
                    {"role": "system", "content": "You are a query decomposition assistant. Respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # Lower temperature for consistent output
                max_tokens=1000
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error("LLM call failed for decomposition", error=str(e))
            raise

    def parse_sub_questions(self, llm_response: str) -> List[Dict[str, Any]]:
        """Parse sub-questions from LLM response.

        Handles both raw JSON and JSON within markdown code blocks.

        Args:
            llm_response: LLM response string

        Returns:
            List of sub-question dictionaries
        """
        # Try to extract JSON from markdown code block
        code_block_match = re.search(
            r'```(?:json)?\n(.*?)\n```',
            llm_response,
            re.DOTALL | re.IGNORECASE
        )

        if code_block_match:
            json_str = code_block_match.group(1)
        else:
            # Try to find JSON array in the response
            json_match = re.search(r'\[.*\]', llm_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = llm_response

        try:
            parsed = json.loads(json_str)

            # Ensure it's a list
            if isinstance(parsed, dict):
                parsed = [parsed]
            elif not isinstance(parsed, list):
                raise ValueError(f"Expected JSON array, got {type(parsed)}")

            # Validate and normalize each sub-question
            validated = []
            for sq in parsed:
                if not isinstance(sq, dict):
                    continue

                # Ensure required fields
                if "question" not in sq:
                    continue

                normalized = {
                    "question": sq["question"],
                    "query_type": sq.get("query_type", "single"),
                    "target_papers": sq.get("target_papers", []),
                    "rationale": sq.get("rationale", ""),
                }

                validated.append(normalized)

            return validated

        except json.JSONDecodeError as e:
            logger.error("Failed to parse LLM response as JSON", response=llm_response[:200])
            raise ValueError(f"Invalid JSON in LLM response: {e}")

    def _expand_subquestions(
        self,
        sub_questions: List[Dict[str, Any]],
        query: str,
        query_type: QueryType,
        paper_ids: Optional[List[str]],
    ) -> List[Dict[str, Any]]:
        """Expand sub-questions to meet minimum count.

        Args:
            sub_questions: Current sub-questions
            query: Original query
            query_type: Query type
            paper_ids: Available paper IDs

        Returns:
            Expanded list of sub-questions
        """
        expanded = list(sub_questions)

        if query_type == "evolution":
            # Add version-specific questions if needed
            if len(expanded) < self.min_subquestions:
                expanded.append({
                    "question": f"What are the common themes across all versions?",
                    "query_type": "cross_paper",
                    "target_papers": paper_ids or [],
                    "rationale": "Identify overarching patterns in the evolution"
                })

        elif query_type == "cross_paper":
            # Add comparison questions if needed
            if len(expanded) < self.min_subquestions:
                expanded.append({
                    "question": f"What are the key similarities and differences?",
                    "query_type": "cross_paper",
                    "target_papers": paper_ids or [],
                    "rationale": "Direct comparison between papers"
                })

        # Generic expansion
        while len(expanded) < self.min_subquestions:
            expanded.append({
                "question": f"Additional context for: {query}",
                "query_type": "single",
                "target_papers": paper_ids or [],
                "rationale": "Supplementary question for completeness"
            })

        return expanded


class ConvergenceChecker:
    """Checks for convergence in multi-round retrieval.

    Uses LLM to judge whether new information was found in the latest round.
    """

    def __init__(self, similarity_threshold: float = 0.95):
        """Initialize convergence checker.

        Args:
            similarity_threshold: Threshold for chunk similarity
        """
        self.similarity_threshold = similarity_threshold

    def check_convergence_simple(
        self,
        previous_results: List[Dict[str, Any]],
        current_results: List[Dict[str, Any]],
    ) -> bool:
        """Simple convergence check based on chunk overlap.

        Args:
            previous_results: Results from previous round
            current_results: Results from current round

        Returns:
            True if converged (no new information)
        """
        # Extract chunk IDs from previous results
        prev_chunk_ids = {
            c.get("id") or c.get("chunk_id")
            for r in previous_results
            for c in r.get("chunks", [])
        }

        # Extract chunk IDs from current results
        curr_chunk_ids = {
            c.get("id") or c.get("chunk_id")
            for r in current_results
            for c in r.get("chunks", [])
        }

        # Check for new chunks
        new_chunks = curr_chunk_ids - prev_chunk_ids

        # Converged if no new chunks found
        return len(new_chunks) == 0

    async def check_convergence_llm(
        self,
        previous_synthesis: str,
        current_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """LLM-based convergence check.

        Asks LLM to judge whether the latest round added new information.

        Args:
            previous_synthesis: Previous round's synthesized answer
            current_results: Current round's retrieval results

        Returns:
            Dictionary with is_converged, reason, and confidence
        """
        # Build context from current results
        current_context = "\n\n".join([
            f"Sub-question: {r.get('sub_question', 'N/A')}\n"
            f"Results: {len(r.get('chunks', []))} chunks found\n"
            f"Summary: {r.get('summary', 'N/A')[:200]}"
            for r in current_results
        ])

        prompt = f"""You are evaluating whether a retrieval process has converged.

Previous synthesis:
{previous_synthesis[:500]}

Current round results:
{current_context}

Has the current round provided new, non-redundant information that should be included in the final answer?

Respond with JSON in this format:
{{
  "is_converged": true/false,
  "reason": "Explanation of why convergence was or was not reached",
  "confidence": 0.0-1.0
}}

Guidelines:
- is_converged=true if no meaningful new information was found
- is_converged=false if new relevant information was discovered
- confidence should reflect your certainty in the judgment"""

        try:
            from app.utils.zhipu_client import get_llm_client
            
            llm_client = get_llm_client()
            
            response = await llm_client.chat_completion(
                messages=[
                    {"role": "system", "content": "You are a convergence evaluation assistant. Respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=500
            )

            content = response.choices[0].message.content

            # Parse JSON response
            try:
                result = json.loads(content)
            except json.JSONDecodeError:
                # Try to extract JSON from response
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group(0))
                else:
                    raise

            return {
                "is_converged": result.get("is_converged", False),
                "reason": result.get("reason", "No reason provided"),
                "confidence": result.get("confidence", 0.5),
            }

        except Exception as e:
            logger.error("LLM convergence check failed", error=str(e))
            # Fallback to not converged
            return {
                "is_converged": False,
                "reason": f"Convergence check failed: {str(e)}",
                "confidence": 0.0,
            }


# Convenience functions
async def decompose_query(
    query: str,
    query_type: Optional[QueryType] = None,
    paper_ids: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Decompose query into sub-questions.

    Convenience function that creates a QueryDecomposer instance
    and calls decompose_query.

    Args:
        query: User query
        query_type: Query type (auto-detected if None)
        paper_ids: Available paper IDs

    Returns:
        List of sub-question dictionaries
    """
    decomposer = QueryDecomposer()
    return await decomposer.decompose_query(query, query_type, paper_ids)


def classify_query(query: str) -> QueryType:
    """Classify query type.

    Args:
        query: User query

    Returns:
        Query type: single, cross_paper, or evolution
    """
    decomposer = QueryDecomposer()
    return decomposer.classify_query(query)
