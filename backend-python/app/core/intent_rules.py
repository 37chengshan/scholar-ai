"""Intent classification rules for query understanding.

Rule-based intent detection for 4 query types:
- compare: Multi-paper comparison queries
- evolution: Evolution/development analysis queries
- summary: Paper summary requests
- question: Single-paper questions (default)

Zero-latency, zero-cost approach using keyword + pattern matching.
"""

import re
from typing import Dict, List


INTENT_RULES: Dict[str, Dict[str, List | str]] = {
    "compare": {
        "keywords": [
            "对比", "比较", "区别", "差异", "vs", "compare", "versus",
            "comparison", "不同", "相同", "优劣", "优缺点"
        ],
        "patterns": [
            r"(.+)和(.+)的(区别|差异|对比)",
            r"比较(.+)与(.+)",
            r"(.+)\s+vs\s+(.+)",
            r"(.+)和(.+)哪个(更好|更优)",
        ],
        "description": "多论文对比查询",
    },
    "evolution": {
        "keywords": [
            "演进", "发展", "演变", "历史", "evolution", "timeline",
            "进化", "进展", "历程"
        ],
        "patterns": [
            r"从(.+)到(.+)的(发展|演进|演变)",
            r"(.+)的(演进过程|发展历程)",
            r"(.+)的发展历史",
        ],
        "description": "演进分析查询",
    },
    "summary": {
        "keywords": [
            "总结", "摘要", "概述", "主要", "核心", "贡献",
            "归纳", "要点"
        ],
        "patterns": [
            r"总结(一下)?(.+)",
            r"(.+)的(主要贡献|核心思想)",
            r"(概述|简介)(.+)",
        ],
        "description": "论文摘要查询",
    },
    "question": {
        "keywords": [],
        "patterns": [],
        "description": "单论文问答（默认）",
    },
}


def detect_intent(query: str) -> str:
    """Detect query intent using rule-based matching.

    Args:
        query: User query string

    Returns:
        Intent label: "compare", "evolution", "summary", or "question" (default)

    Examples:
        >>> detect_intent("YOLOv3和YOLOv4的区别")
        'compare'
        >>> detect_intent("从YOLOv1到YOLOv4的演进")
        'evolution'
        >>> detect_intent("总结一下这篇论文")
        'summary'
        >>> detect_intent("什么是注意力机制")
        'question'
    """
    query_lower = query.lower()

    # Check each intent (except default)
    for intent in ["compare", "evolution", "summary"]:
        rules = INTENT_RULES[intent]

        # Check keywords first (faster)
        for keyword in rules["keywords"]:
            if keyword in query_lower:
                return intent

        # Check patterns (more complex matching)
        for pattern in rules["patterns"]:
            if re.search(pattern, query):
                return intent

    # Default to question intent
    return "question"