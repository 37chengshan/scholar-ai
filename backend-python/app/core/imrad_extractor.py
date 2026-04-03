"""IMRaD structure extraction from parsed PDF content

Extracts Introduction, Methods, Results, and Conclusion sections from
academic papers. Supports both English and Chinese section headers.

Features:
- Pattern matching for standard academic section headers
- Page number tracking for each section
- Fallback for papers without clear IMRaD structure
- Confidence scoring based on header detection
- LLM-assisted extraction for non-standard papers (D-05)
"""

import re
import json
from typing import List, Dict, Any, Optional

from zhipuai import ZhipuAI
from app.core.config import settings
from app.utils.logger import logger


IMRAD_PATTERNS = {
    "introduction": [
        r"^\s*introduction",
        r"^\s*background",
        r"^\s*1\.\s*introduction",
        r"^\s*i\s*\.\s*introduction",
        r"introduction and background",
        r"^\s*引言",
        r"^\s*简介",
        r"^\s*背景",
        r"^\s*1[\.\s]引言",
        r"^\s*一[\.、\s]",
        r"^\s*前言",
        r"^\s*绪论",
        r"^\s*研究背景",
    ],
    "methods": [
        r"^\s*methods?",
        r"^\s*methodology",
        r"^\s*materials?\s*(and|&)\s*methods?",
        r"^\s*experimental\s*(setup|methods?)",
        r"^\s*2\.\s*methods?",
        r"^\s*ii\s*\.\s*methods?",
        r"^\s*方法",
        r"^\s*研究方法",
        r"^\s*实验方法",
        r"^\s*材料与方法",
        r"^\s*2[\.\s]方法",
        r"^\s*二[\.、\s]",
        r"^\s*实验设计",
        r"^\s*方法论",
    ],
    "results": [
        r"^\s*results?",
        r"^\s*findings",
        r"^\s*3\.\s*results?",
        r"^\s*iii\s*\.\s*results?",
        r"results?\s*(and|&)\s*discussion",
        r"^\s*结果",
        r"^\s*实验结果",
        r"^\s*研究发现",
        r"^\s*3[\.\s]结果",
        r"^\s*三[\.、\s]",
        r"^\s*结果与分析",
        r"^\s*研究结果",
    ],
    "conclusion": [
        r"^\s*conclusions?",
        r"^\s*discussion",
        r"^\s*4\.\s*conclusions?",
        r"^\s*iv\s*\.\s*conclusions?",
        r"^\s*summary",
        r"^\s*concluding\s*remarks",
        r"^\s*结论",
        r"^\s*讨论",
        r"^\s*总结",
        r"^\s*4[\.\s]结论",
        r"^\s*四[\.、\s]",
        r"^\s*结论与讨论",
        r"^\s*总结与展望",
        r"^\s*结论与展望",
    ]
}


def is_section_header(text: str, section: str) -> bool:
    """Check if text matches any pattern for the given section.

    Args:
        text: The text to check
        section: Section name (introduction, methods, results, conclusion)

    Returns:
        True if text matches any pattern for the section
    """
    text_lower = text.strip().lower()
    patterns = IMRAD_PATTERNS.get(section, [])
    return any(re.match(pattern, text_lower, re.IGNORECASE) for pattern in patterns)


def detect_section(text: str) -> Optional[str]:
    """Detect which section a header belongs to.

    Args:
        text: The header text to analyze

    Returns:
        Section name if matched, None otherwise
    """
    for section in ["introduction", "methods", "results", "conclusion"]:
        if is_section_header(text, section):
            return section
    return None


def extract_imrad_structure(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Extract IMRaD structure from parsed document items.

    Args:
        items: List of dicts with 'type', 'text', 'page', 'bbox'

    Returns:
        Dict with sections containing text, page ranges, and item count.
        Each section has: content, word_count, page_start, page_end, confidence
        Result also includes _estimated flag and _confidence_score
    """
    sections = {
        "introduction": {"texts": [], "page_start": None, "page_end": None},
        "methods": {"texts": [], "page_start": None, "page_end": None},
        "results": {"texts": [], "page_start": None, "page_end": None},
        "conclusion": {"texts": [], "page_start": None, "page_end": None},
    }
    current_section = "introduction"  # Default assumption
    detected_headers = set()

    for item in items:
        if item.get("type") != "text":
            continue

        text = item.get("text", "").strip()
        if not text:
            continue

        # Check if this is a section header
        detected = detect_section(text)
        if detected:
            current_section = detected
            detected_headers.add(detected)
            continue  # Don't include header text in content

        # Add text to current section
        if current_section in sections:
            sections[current_section]["texts"].append({
                "text": text,
                "page": item.get("page"),
                "bbox": item.get("bbox")
            })

            # Update page range
            page = item.get("page")
            if page is not None:
                if sections[current_section]["page_start"] is None:
                    sections[current_section]["page_start"] = page
                sections[current_section]["page_end"] = page

    # Check if any headers were detected
    has_headers = len(detected_headers) > 0

    # Fallback: distribute content evenly if no headers found
    if not has_headers:
        return _apply_fallback_strategy(items, sections)

    # Build final structure with confidence scoring
    result = {}
    total_words = 0
    for section_name, data in sections.items():
        combined_text = "\n\n".join(t["text"] for t in data["texts"])
        word_count = len(combined_text.split()) if combined_text else 0
        total_words += word_count

        # Calculate confidence based on header detection
        confidence = 1.0 if section_name in detected_headers else 0.5

        result[section_name] = {
            "content": combined_text,
            "word_count": word_count,
            "page_start": data["page_start"],
            "page_end": data["page_end"],
            "confidence": confidence,
        }

    # Overall confidence score
    result["_estimated"] = False
    result["_confidence_score"] = len(detected_headers) / 4.0
    result["_detected_headers"] = list(detected_headers)

    return result


def _apply_fallback_strategy(
    items: List[Dict[str, Any]],
    sections: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    """Apply fallback strategy when no section headers detected.

    Distributes content evenly across IMRaD sections based on position.

    Args:
        items: All document items
        sections: Section structure to populate

    Returns:
        IMRaD structure with estimated content distribution
    """
    # Collect all text items
    all_texts = []
    for item in items:
        if item.get("type") == "text":
            text = item.get("text", "").strip()
            if text:
                all_texts.append({
                    "text": text,
                    "page": item.get("page"),
                    "bbox": item.get("bbox")
                })

    n = len(all_texts)
    if n == 0:
        return _create_empty_result()

    # Distribute content evenly: 25% each section
    intro_texts = all_texts[:max(1, n // 4)]
    methods_texts = all_texts[max(1, n // 4):max(1, n // 2)]
    results_texts = all_texts[max(1, n // 2):max(1, 3 * n // 4)]
    conclusion_texts = all_texts[max(1, 3 * n // 4):]

    result = {}
    section_texts_map = {
        "introduction": intro_texts,
        "methods": methods_texts,
        "results": results_texts,
        "conclusion": conclusion_texts,
    }

    for section_name, texts in section_texts_map.items():
        combined_text = "\n\n".join(t["text"] for t in texts)
        page_start = texts[0]["page"] if texts else None
        page_end = texts[-1]["page"] if texts else None

        result[section_name] = {
            "content": combined_text,
            "word_count": len(combined_text.split()) if combined_text else 0,
            "page_start": page_start,
            "page_end": page_end,
            "confidence": 0.3,  # Low confidence for estimated content
        }

    result["_estimated"] = True
    result["_confidence_score"] = 0.25  # Low overall confidence
    result["_detected_headers"] = []

    return result


def _create_empty_result() -> Dict[str, Any]:
    """Create empty IMRaD result structure."""
    return {
        "introduction": {
            "content": "",
            "word_count": 0,
            "page_start": None,
            "page_end": None,
            "confidence": 0.0,
        },
        "methods": {
            "content": "",
            "word_count": 0,
            "page_start": None,
            "page_end": None,
            "confidence": 0.0,
        },
        "results": {
            "content": "",
            "word_count": 0,
            "page_start": None,
            "page_end": None,
            "confidence": 0.0,
        },
        "conclusion": {
            "content": "",
            "word_count": 0,
            "page_start": None,
            "page_end": None,
            "confidence": 0.0,
        },
        "_estimated": True,
        "_confidence_score": 0.0,
        "_detected_headers": [],
    }


def extract_metadata(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Extract paper metadata (title, authors, abstract) from first page.
    Uses heuristics based on position and formatting.

    Args:
        items: List of parsed document items

    Returns:
        Dict with title, authors, abstract, keywords, doi
    """
    metadata = {
        "title": None,
        "authors": [],
        "abstract": None,
        "keywords": [],
        "doi": None,
    }

    # Get first page items only
    first_page_items = [
        i for i in items
        if i.get("page") == 1 and i.get("type") == "text"
    ]

    if not first_page_items:
        return metadata


async def extract_imrad_enhanced(
    items: List[Dict[str, Any]],
    markdown: str,
    paper_metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """Enhanced IMRaD extraction with LLM assistance per D-05.

    Uses hybrid approach: rule-based extraction first, then LLM assistance
    if confidence is below threshold.

    Args:
        items: Parsed items from Docling
        markdown: Full document markdown
        paper_metadata: Paper metadata (title, abstract, etc.)

    Returns:
        IMRaD structure with confidence scores. Guaranteed confidence >= 0.75
        for LLM-assisted results.

    Example:
        >>> result = await extract_imrad_enhanced(items, markdown, metadata)
        >>> result["_confidence_score"] >= 0.75
        True
    """
    # Step 1: Rule-based extraction
    rule_based_result = extract_imrad_structure(items)
    confidence = rule_based_result.get("_confidence_score", 0)

    # Step 2: High confidence - return as-is
    if confidence >= 0.75:  # LOCKED threshold per D-05
        logger.info(
            "High confidence IMRaD extraction, skipping LLM",
            confidence=confidence
        )
        return rule_based_result

    # Step 3: Low confidence - use LLM (per D-05)
    logger.info(
        "Low confidence IMRaD extraction, using LLM assistance",
        confidence=confidence
    )

    try:
        llm_result = await _extract_with_llm(
            markdown=markdown,
            model="glm-4-flash"  # LOCKED model per D-05
        )

        # Step 4: Merge results
        final_result = _merge_imrad_results(
            rule_based_result,
            llm_result
        )

        return final_result

    except Exception as e:
        logger.error(
            "LLM-assisted IMRaD extraction failed, returning rule-based result",
            error=str(e)
        )
        # Return rule-based result even if LLM fails
        return rule_based_result


async def _extract_with_llm(markdown: str, model: str) -> Dict[str, Any]:
    """Use LLM for IMRaD structure extraction.

    Args:
        markdown: Full document markdown
        model: LLM model to use (should be "glm-4-flash")

    Returns:
        IMRaD structure from LLM

    Raises:
        Exception: If LLM API call fails
    """
    client = ZhipuAI(api_key=settings.ZHIPU_API_KEY)

    # Prompt from D-05 (lines 327-346 in CONTEXT.md)
    prompt = f"""分析这篇学术论文的结构，识别以下章节：

1. Introduction（引言）
2. Methods（方法）
3. Results（结果）
4. Conclusion（结论）

对于每个章节，提供：
- 起始页码
- 结束页码
- 置信度（0-1）

如果某个章节不存在，标记为 null。

输出 JSON 格式：
{{
  "introduction": {{"page_start": X, "page_end": Y, "confidence": 0.9}},
  ...
}}

论文内容：
{markdown[:10000]}
"""

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )

    # Parse JSON response
    content = response.choices[0].message.content

    # Try to extract JSON from response
    try:
        # Remove markdown code blocks if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        return json.loads(content)
    except json.JSONDecodeError as e:
        logger.error(
            "Failed to parse LLM IMRaD response as JSON",
            error=str(e),
            content=content[:500]
        )
        raise ValueError(f"Invalid JSON from LLM: {e}")


def _merge_imrad_results(
    rule_based: Dict[str, Any],
    llm: Dict[str, Any]
) -> Dict[str, Any]:
    """Merge rule-based and LLM results.

    Prefers higher confidence results for each section.

    Args:
        rule_based: Result from rule-based extraction
        llm: Result from LLM extraction

    Returns:
        Merged IMRaD structure with confidence >= 0.75
    """
    merged = {}

    for section in ["introduction", "methods", "results", "conclusion"]:
        rule_data = rule_based.get(section, {})
        llm_data = llm.get(section, {})

        # Handle None values from LLM
        if llm_data is None:
            llm_data = {}

        # Ensure rule_data is a dict
        if not isinstance(rule_data, dict):
            rule_data = {}

        # Prefer higher confidence result
        rule_confidence = rule_data.get("confidence", 0) if isinstance(rule_data, dict) else 0
        llm_confidence = llm_data.get("confidence", 0) if isinstance(llm_data, dict) else 0

        if rule_confidence >= llm_confidence:
            merged[section] = rule_data
        else:
            # Use LLM result but ensure it has the right structure
            merged[section] = {
                "content": rule_data.get("content", ""),
                "word_count": rule_data.get("word_count", 0),
                "page_start": llm_data.get("page_start") if isinstance(llm_data, dict) else None,
                "page_end": llm_data.get("page_end") if isinstance(llm_data, dict) else None,
                "confidence": llm_data.get("confidence", 0.75) if isinstance(llm_data, dict) else 0.75,
            }

    # LLM-assisted results have minimum 0.75 confidence
    merged["_estimated"] = False
    merged["_confidence_score"] = max(
        rule_based.get("_confidence_score", 0),
        0.75  # LLM-assisted minimum confidence
    )
    merged["_detected_headers"] = rule_based.get("_detected_headers", [])

    return merged

    # Title: usually first substantial text on first page
    for item in first_page_items[:5]:  # Check first 5 items
        text = item.get("text", "").strip()
        # Heuristic: title is typically 20-200 chars, not too short
        if len(text) > 10 and len(text) < 300:
            # Skip if it looks like a header or label
            if not re.match(r"^(abstract|摘要|introduction|引言)", text, re.IGNORECASE):
                metadata["title"] = text
                break

    # Authors: look for email patterns or author-like formatting
    author_candidates = []
    for item in first_page_items[:20]:  # Check first 20 items
        text = item.get("text", "").strip()

        # Skip if it's the title
        if text == metadata["title"]:
            continue

        # Email pattern indicates author
        if "@" in text:
            # Extract name part before email
            parts = text.split("<")
            if parts:
                author_candidates.append(parts[0].strip())
            continue

        # Name pattern: "First Last" or "F. Last"
        if re.search(r"[A-Z][a-z]+\s+[A-Z][a-z]+", text):
            if len(text) < 100:  # Reasonable name length
                author_candidates.append(text)

        # Limit authors
        if len(author_candidates) >= 10:
            break

    # Clean up author list
    metadata["authors"] = list(dict.fromkeys(author_candidates))[:10]  # Remove duplicates, max 10

    # Abstract: look for "Abstract" or "摘要" header followed by text
    abstract_started = False
    abstract_texts = []
    for item in first_page_items:
        text = item.get("text", "").strip()

        if re.match(r"^\s*(abstract|摘要)", text, re.IGNORECASE):
            abstract_started = True
            continue

        if abstract_started:
            # Stop if we hit another section header
            if detect_section(text) or re.match(r"^\s*(introduction|引言|1\.\s)", text, re.IGNORECASE):
                break
            if len(text) > 20:  # Abstract paragraphs are substantial
                abstract_texts.append(text)
            if len(" ".join(abstract_texts)) > 2000:  # Limit abstract length
                break

    if abstract_texts:
        metadata["abstract"] = " ".join(abstract_texts)

    # Keywords: look for "Keywords" or "关键词" section
    for item in first_page_items:
        text = item.get("text", "").strip()
        if re.match(r"^\s*(keywords|关键词)", text, re.IGNORECASE):
            # Keywords might be on same line or next item
            keyword_text = re.sub(r"^\s*(keywords|关键词)[：:]?\s*", "", text, flags=re.IGNORECASE)
            if keyword_text:
                metadata["keywords"] = [k.strip() for k in re.split(r"[,;，；]", keyword_text) if k.strip()]
            break

    # DOI: pattern matching
    for item in first_page_items:
        text = item.get("text", "").strip()
        # DOI pattern: 10.xxxx/xxxxx
        doi_match = re.search(r"10\.\d{4,}/[^\s]+", text)
        if doi_match:
            metadata["doi"] = doi_match.group(0)
            break

    return metadata
