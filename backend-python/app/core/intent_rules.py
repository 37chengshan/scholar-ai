"""Intent classification rules for query understanding.

Rule-based intent detection for 8 query types:
- question: Single-paper questions (default)
- compare: Multi-paper comparison queries
- evolution: Evolution/development analysis queries
- summary: Paper summary requests
- method: Methodology-related queries
- results: Results/findings queries
- code: Code/implementation queries
- references: References/citations queries

Zero-latency, zero-cost approach using keyword + pattern matching.

Per D-22: 8 intent types with comprehensive coverage.
"""

import re
from typing import Dict, List


INTENT_RULES: Dict[str, Dict[str, List | str]] = {
    "compare": {
        "keywords": [
            "对比",
            "比较",
            "区别",
            "差异",
            "vs",
            "compare",
            "versus",
            "comparison",
            "不同",
            "相同",
            "优劣",
            "优缺点",
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
            "演进",
            "发展",
            "演变",
            "历史",
            "evolution",
            "timeline",
            "进化",
            "进展",
            "历程",
        ],
        "patterns": [
            r"从(.+)到(.+)的(发展|演进|演变)",
            r"(.+)的(演进过程|发展历程)",
            r"(.+)的发展历史",
        ],
        "description": "演进分析查询",
    },
    "summary": {
        "keywords": ["总结", "摘要", "概述", "主要", "核心", "贡献", "归纳", "要点"],
        "patterns": [
            r"总结(一下)?(.+)",
            r"(.+)的(主要贡献|核心思想)",
            r"(概述|简介)(.+)",
        ],
        "description": "论文摘要查询",
    },
    "method": {
        "keywords": [
            "method",
            "methodology",
            "approach",
            "technique",
            "方法",
            "方法论",
            "技术",
            "实现方法",
            "算法",
        ],
        "patterns": [
            r"(how does|explain the) (method|methodology|approach)",
            r"what (method|approach|technique)",
            r"(.+)的(方法|方法论)",
            r"(method|methodology|approach) (of|for|section)",
        ],
        "description": "方法论相关查询",
    },
    "results": {
        "keywords": [
            "results",
            "findings",
            "outcomes",
            "data",
            "结果",
            "发现",
            "数据",
            "实验结果",
            "性能",
        ],
        "patterns": [
            r"(what are|show) (the )?(results|findings|outcomes)",
            r"(.+)的(结果|发现)",
            r"(results|findings) (of|from)",
        ],
        "description": "结果与发现查询",
    },
    "code": {
        "keywords": [
            "code",
            "implementation",
            "algorithm",
            "script",
            "代码",
            "实现",
            "算法",
            "源码",
            "开源",
        ],
        "patterns": [
            r"(show|give me) (the )?code",
            r"(implementation|code) (details|for)",
            r"(.+)的(代码|实现)",
        ],
        "description": "代码与实现查询",
    },
    "references": {
        "keywords": [
            "references",
            "citations",
            "bibliography",
            "related",
            "参考文献",
            "引用",
            "相关工作",
            "文献",
        ],
        "patterns": [
            r"(list|show) (references|citations)",
            r"(.+)的参考文献",
            r"(references|citations|bibliography) (of|for)",
            r"related work",
        ],
        "description": "参考文献查询",
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
        Intent label: one of 8 intents ("compare", "evolution", "summary",
                      "method", "results", "code", "references", or "question")

    Examples:
        >>> detect_intent("YOLOv3和YOLOv4的区别")
        'compare'
        >>> detect_intent("从YOLOv1到YOLOv4的演进")
        'evolution'
        >>> detect_intent("总结一下这篇论文")
        'summary'
        >>> detect_intent("论文使用的方法是什么")
        'method'
        >>> detect_intent("实验结果怎么样")
        'results'
        >>> detect_intent("有代码实现吗")
        'code'
        >>> detect_intent("列出参考文献")
        'references'
        >>> detect_intent("什么是注意力机制")
        'question'
    """
    query_lower = query.lower()

    # Check each intent (except default "question")
    for intent in [
        "compare",
        "evolution",
        "summary",
        "method",
        "results",
        "code",
        "references",
    ]:
        rules = INTENT_RULES[intent]

        # Check keywords first (faster)
        for keyword in rules["keywords"]:
            if keyword in query_lower:
                return intent

        # Check patterns (more complex matching)
        for pattern in rules["patterns"]:
            if re.search(pattern, query, re.IGNORECASE):
                return intent

    # Default to question intent
    return "question"
