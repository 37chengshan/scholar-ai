"""Query metadata extraction service.

Extracts metadata filters from user queries:
- Year range (2023年, 2020-2023, 最近3年)
- Author name (张三的研究, LeCun的论文)
- Keywords (关于注意力机制的)

Uses regex patterns for zero-latency, zero-cost extraction (per D-07).
"""

import re
from datetime import datetime
from typing import Any, Dict, Optional, Tuple


def extract_year_range(query: str) -> Optional[Tuple[int, int]]:
    """Extract year range from query using regex patterns.

    Supports 3 patterns (per D-08):
    1. "2023年" → (2023, 2023)
    2. "2020-2023" → (2020, 2023)
    3. "最近3年" → (current_year - 3, current_year)

    Args:
        query: User query string

    Returns:
        Tuple of (start_year, end_year) or None if not found

    Examples:
        >>> extract_year_range("2023年的论文")
        (2023, 2023)
        >>> extract_year_range("2020-2023")
        (2020, 2023)
        >>> extract_year_range("最近3年")
        (2021, 2024)  # Assuming current year is 2024
    """
    current_year = datetime.now().year

    # Pattern 1: "2023年"
    match = re.search(r"(\d{4})年", query)
    if match:
        year = int(match.group(1))
        return (year, year)

    # Pattern 2: "2020-2023"
    match = re.search(r"(\d{4})-(\d{4})", query)
    if match:
        start_year = int(match.group(1))
        end_year = int(match.group(2))
        return (start_year, end_year)

    # Pattern 3: "最近3年"
    match = re.search(r"最近(\d+)年", query)
    if match:
        years = int(match.group(1))
        return (current_year - years, current_year)

    return None


def extract_author(query: str) -> Optional[str]:
    """Extract author name from query using patterns.

    Patterns (per D-09):
    1. "张三的研究" → "张三"
    2. "LeCun的论文" → "LeCun"
    3. "author: Hinton" → "Hinton"

    Args:
        query: User query string

    Returns:
        Author name string or None if not found

    Examples:
        >>> extract_author("张三的研究")
        '张三'
        >>> extract_author("LeCun的论文")
        'LeCun'
        >>> extract_author("author: Hinton")
        'Hinton'
    """
    patterns = [
        r'author[:\s]+([A-Za-z\u4e00-\u9fa5]+)',  # "author: Hinton" or "author: 张三" (check first)
        r'(?:^|年|\s)([\u4e00-\u9fa5]{2,3})的',  # Chinese name after start, "年" or space
        r'([A-Z][a-z]+(?:[A-Z][a-z]+)?)的',  # English name (capitalized) before "的"
    ]

    for pattern in patterns:
        match = re.search(pattern, query)
        if match:
            author = match.group(1).strip()
            # Clean up extra characters
            author = re.sub(r"[\s\-_:]+$", "", author)
            return author

    return None


def extract_keywords(query: str) -> Optional[str]:
    """Extract domain keywords from query using patterns.

    Patterns (per D-10):
    1. "关于注意力机制的" → "注意力机制"
    2. "深度学习相关" → "深度学习"

    Args:
        query: User query string

    Returns:
        Keyword string or None if not found

    Examples:
        >>> extract_keywords("关于注意力机制的")
        '注意力机制'
        >>> extract_keywords("深度学习相关")
        '深度学习'
    """
    patterns = [
        r"关于(.+)的",  # "关于注意力机制的"
        r"(.+)相关",  # "深度学习相关"
    ]

    for pattern in patterns:
        match = re.search(pattern, query)
        if match:
            keywords = match.group(1).strip()
            return keywords

    return None


def extract_metadata_filters(query: str) -> Dict[str, Any]:
    """Extract all metadata filters from query.

    Combines year_range, author, and keywords into a single dict (per D-11).

    Args:
        query: User query string

    Returns:
        Dict with optional keys: year_range, author, keywords

    Examples:
        >>> extract_metadata_filters("2023年张三的关于注意力机制的论文")
        {
            'year_range': (2023, 2023),
            'author': '张三',
            'keywords': '注意力机制'
        }

    Note:
        Empty dict returned if no filters found.
    """
    filters: Dict[str, Any] = {}

    # Extract year range
    year_range = extract_year_range(query)
    if year_range:
        filters["year_range"] = year_range

    # Extract author
    author = extract_author(query)
    if author:
        filters["author"] = author

    # Extract keywords
    keywords = extract_keywords(query)
    if keywords:
        filters["keywords"] = keywords

    return filters