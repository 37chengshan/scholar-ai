"""Complexity Router for Agent-Native Chat.

Implements dual-layer routing mechanism:
- Rule-first matching (complex rules priority)
- LLM fallback classification (async)
- Default-safe fallback

Routing strategy:
1. Complex rules match first (prevent simple swallowing)
2. Simple rules match second
3. No match returns default (method: "default", complexity: "simple")
"""

import re
import json
import asyncio
from typing import Any, Dict, Optional

from app.utils.logger import logger


# Complex rules (priority match) - more specific patterns
COMPLEX_RULES = [
    # Comparison type
    (r"比较.*差异", "complex"),
    (r"比较.*分析", "complex"),
    (r"对比.*不同", "complex"),
    (r".*的区别", "complex"),
    (r".*和.*的差异", "complex"),
    (r".*与.*对比", "complex"),
    (r".*和.*的比较", "complex"),
    (r".*论文.*比较", "complex"),
    # Evolution type
    (r"演进.*历程", "complex"),
    (r".*发展历程", "complex"),
    (r"版本演进", "complex"),
    (r"从.*到.*的演进", "complex"),
    (r".*发展脉络", "complex"),
    # Multi-paper type
    (r"这几篇.*论文", "complex"),
    (r"多个论文.*", "complex"),
    (r"多篇.*", "complex"),
    (r"所有论文.*", "complex"),
    # Analysis type
    (r"优缺点", "complex"),
    (r"研究现状", "complex"),
    (r"综述", "complex"),
    (r"局限性", "complex"),
    (r"改进建议", "complex"),
    (r"未来.*方向", "complex"),
]

# Simple rules (narrowed to clear scenarios)
SIMPLE_RULES = [
    # Definition type (narrowed)
    (r"什么是", "simple"),
    (r"定义.*是", "simple"),
    (r"解释.*的", "simple"),
    # Summary type (narrowed)
    (r"摘要.*论文", "simple"),
    (r"总结这篇.*内容", "simple"),
    (r"概括.*主要内容", "simple"),
]

# Confidence thresholds
RULE_HIGH_CONFIDENCE = 0.9
LLM_FALLBACK_TIMEOUT = 5.0  # seconds


class ComplexityRouter:
    """Complexity router with rule-first + LLM fallback strategy.

    Features:
    - Complex rules match first (priority)
    - Simple rules match second (narrowed)
    - LLM async fallback for uncertain cases
    - Default-safe fallback on errors

    Usage:
        router = ComplexityRouter()
        result = router.route("什么是注意力机制")  # sync, rule-based

        router_with_llm = ComplexityRouter(llm_client=client)
        result = await router_with_llm.route_async("模糊问题")  # async, LLM fallback
    """

    def __init__(self, llm_client: Optional[Any] = None):
        """Initialize router.

        Args:
            llm_client: Optional LLM client for fallback (must have chat_completion method)
        """
        self.llm_client = llm_client
        self._compile_rules()

        logger.info(
            "ComplexityRouter initialized",
            complex_rules=len(COMPLEX_RULES),
            simple_rules=len(SIMPLE_RULES),
            has_llm_client=bool(llm_client)
        )

    def _compile_rules(self) -> None:
        """Pre-compile regex patterns for performance."""
        self._complex_patterns = [
            (re.compile(pattern, re.IGNORECASE), complexity)
            for pattern, complexity in COMPLEX_RULES
        ]
        self._simple_patterns = [
            (re.compile(pattern, re.IGNORECASE), complexity)
            for pattern, complexity in SIMPLE_RULES
        ]

    def route(self, query: str) -> Dict[str, Any]:
        """Route query based on rules (sync, no LLM).

        Complex rules match first, then simple rules.
        No match returns default.

        Args:
            query: User query string

        Returns:
            Dict with:
                - complexity: "simple" or "complex"
                - method: "rule" or "default"
                - confidence: 0.0-1.0
                - matched_pattern: matched pattern (optional)
        """
        # Edge case: empty query
        if not query or not query.strip():
            return self._default_result()

        # Clean query for processing
        clean_query = query.strip()

        # Edge case: very long query - truncate for pattern matching
        if len(clean_query) > 1000:
            clean_query = clean_query[:1000]

        # Complex rules first (priority match)
        for pattern, complexity in self._complex_patterns:
            if pattern.search(clean_query):
                logger.info(
                    "Complex rule matched",
                    query=query[:100],
                    pattern=pattern.pattern
                )
                return {
                    "complexity": complexity,
                    "method": "rule",
                    "confidence": RULE_HIGH_CONFIDENCE,
                    "matched_pattern": pattern.pattern
                }

        # Simple rules second (narrowed scenarios)
        for pattern, complexity in self._simple_patterns:
            if pattern.search(clean_query):
                logger.info(
                    "Simple rule matched",
                    query=query[:100],
                    pattern=pattern.pattern
                )
                return {
                    "complexity": complexity,
                    "method": "rule",
                    "confidence": RULE_HIGH_CONFIDENCE,
                    "matched_pattern": pattern.pattern
                }

        # No match - return default
        logger.info(
            "No rule match, returning default",
            query=query[:100]
        )
        return self._default_result()

    async def route_async(self, query: str) -> Dict[str, Any]:
        """Route query with optional LLM fallback (async).

        Strategy:
        1. Try rule matching first
        2. If no match and LLM available, try LLM classification
        3. Fallback to default on errors

        Args:
            query: User query string

        Returns:
            Dict with:
                - complexity: "simple" or "complex"
                - method: "rule", "llm", "hybrid", or "default"
                - confidence: 0.0-1.0
                - reasoning: LLM reasoning (optional)
        """
        # First try sync rule matching
        rule_result = self.route(query)

        # If rule matched, return immediately
        if rule_result["method"] == "rule":
            return rule_result

        # No rule match - try LLM fallback
        if self.llm_client:
            try:
                llm_result = await self._classify_with_llm(query)
                return llm_result
            except TimeoutError:
                logger.warning("LLM timeout, fallback to default")
                return self._default_result()
            except Exception as e:
                logger.error("LLM classification failed", error=str(e))
                return self._default_result()

        # No LLM client - return default
        return self._default_result()

    async def _classify_with_llm(self, query: str) -> Dict[str, Any]:
        """Classify query complexity using LLM.

        Args:
            query: User query string

        Returns:
            Dict with complexity, method, confidence, reasoning
        """
        if not self.llm_client:
            return self._default_result()

        prompt = f"""分析以下问题的复杂度，判断应该用简单RAG还是复杂Agent处理。

问题: {query}

判断标准:
- simple: 定义类、摘要类、单点查询
- complex: 比较类、演进类、多论文分析、综述类

返回JSON格式（注意花括号需要转义）:
{{"complexity": "simple或complex", "reasoning": "判断原因"}}

只返回JSON，不要其他内容。"""

        try:
            # Call LLM with timeout
            response = await asyncio.wait_for(
                self.llm_client.chat_completion(
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=200,
                    temperature=0.3
                ),
                timeout=LLM_FALLBACK_TIMEOUT
            )

            # Parse response
            content = response.choices[0].message.content.strip()

            # Extract JSON from response
            json_result = self._parse_llm_json(content)

            if json_result:
                complexity = json_result.get("complexity", "simple")
                reasoning = json_result.get("reasoning", "")

                logger.info(
                    "LLM classification result",
                    query=query[:100],
                    complexity=complexity,
                    reasoning=reasoning[:50]
                )

                return {
                    "complexity": complexity,
                    "method": "llm",
                    "confidence": 0.7,
                    "reasoning": reasoning
                }

            # JSON parse failed
            logger.warning("LLM JSON parse failed, fallback to default")
            return self._default_result()

        except asyncio.TimeoutError:
            logger.warning("LLM call timed out")
            raise TimeoutError("LLM timeout")
        except Exception as e:
            logger.error("LLM classification error", error=str(e))
            raise

    def _parse_llm_json(self, content: str) -> Optional[Dict[str, Any]]:
        """Parse JSON from LLM response content.

        Handles:
        - Plain JSON
        - JSON in markdown code blocks
        - Dirty JSON with extra text

        Args:
            content: LLM response content

        Returns:
            Parsed dict or None
        """
        try:
            # Try direct parse
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # Try to find JSON in content
        json_start = content.find("{")
        json_end = content.rfind("}") + 1

        if json_start >= 0 and json_end > json_start:
            try:
                return json.loads(content[json_start:json_end])
            except json.JSONDecodeError:
                pass

        # Try to clean markdown code blocks
        if "```" in content:
            # Remove markdown formatting
            cleaned = content.replace("```json", "").replace("```", "").strip()
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                pass

        return None

    def _default_result(self) -> Dict[str, Any]:
        """Return default result (safe fallback).

        Returns:
            Default routing result
        """
        return {
            "complexity": "simple",
            "method": "default",
            "confidence": 0.5
        }


# Convenience function for quick routing
def route_query(query: str) -> Dict[str, Any]:
    """Quick routing without LLM (sync).

    Args:
        query: User query string

    Returns:
        Routing result dict
    """
    router = ComplexityRouter()
    return router.route(query)


__all__ = [
    "ComplexityRouter",
    "COMPLEX_RULES",
    "SIMPLE_RULES",
    "route_query",
]