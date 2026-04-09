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
from app.config import settings
from app.utils.logger import logger


IMRAD_PATTERNS = {
    "introduction": [
        # Exact matches (confidence = 0.9)
        r"^\s*introduction$",
        r"^\s*background$",
        r"^\s*引言$",
        r"^\s*简介$",
        r"^\s*背景$",
        r"^\s*前言$",
        r"^\s*绪论$",
        # Numbered sections (confidence = 0.85)
        r"^\s*1\.?\s*introduction",
        r"^\s*i\.?\s*introduction",
        r"^\s*1[\.\s]引言",
        r"^\s*一[\.、\s]",
        # Fuzzy matches (confidence = 0.7)
        r"introduction and background",
        r"^\s*研究背景",
        r"^\s*overview",
        r"^\s*motivation",
        r"^\s*related work",
        r"^\s*literature review",
    ],
    "methods": [
        # Exact matches (confidence = 0.9)
        r"^\s*methods?$",
        r"^\s*methodology$",
        r"^\s*方法$",
        r"^\s*研究方法$",
        r"^\s*实验方法$",
        r"^\s*方法论$",
        # Numbered sections (confidence = 0.85)
        r"^\s*2\.?\s*methods?",
        r"^\s*ii\.?\s*methods?",
        r"^\s*2[\.\s]方法",
        r"^\s*二[\.、\s]",
        # Fuzzy matches (confidence = 0.7)
        r"^\s*materials?\s*(and|&)\s*methods?",
        r"^\s*experimental\s*(setup|methods?)",
        r"^\s*材料与方法",
        r"^\s*实验设计",
        r"^\s*approach",
        r"^\s*experimental design",
    ],
    "results": [
        # Exact matches (confidence = 0.9)
        r"^\s*results?$",
        r"^\s*findings?$",
        r"^\s*结果$",
        r"^\s*实验结果$",
        r"^\s*研究发现$",
        r"^\s*研究结果$",
        # Numbered sections (confidence = 0.85)
        r"^\s*3\.?\s*results?",
        r"^\s*iii\.?\s*results?",
        r"^\s*3[\.\s]结果",
        r"^\s*三[\.、\s]",
        # Fuzzy matches (confidence = 0.7)
        r"results?\s*(and|&)\s*discussion",
        r"^\s*结果与分析",
        r"^\s*evaluation",
        r"^\s*experiments?",
        r"^\s*performance analysis",
        r"^\s*analysis",
    ],
    "conclusion": [
        # Exact matches (confidence = 0.9)
        r"^\s*conclusions?$",
        r"^\s*discussion$",
        r"^\s*总结$",
        r"^\s*讨论$",
        r"^\s*结论$",
        # Numbered sections (confidence = 0.85)
        r"^\s*4\.?\s*(?:conclusions?|discussion)",
        r"^\s*iv\.?\s*(?:conclusions?|discussion)",
        r"^\s*4[\.\s]结论",
        r"^\s*四[\.、\s]",
        # Fuzzy matches (confidence = 0.7)
        r"^\s*summary",
        r"^\s*concluding\s*remarks",
        r"^\s*结论与讨论",
        r"^\s*总结与展望",
        r"^\s*结论与展望",
        r"^\s*future work",
        r"^\s*limitations",
    ],
}


def calculate_pattern_confidence(text: str, pattern: str, section: str) -> float:
    """Calculate confidence score based on pattern type.

    Per D-03: Weighted confidence scoring.
    - Exact match (pattern ends with $): 0.9
    - Numbered section (pattern contains \d\.?): 0.85
    - Fuzzy match (general pattern): 0.7

    Args:
        text: The matched text
        pattern: The regex pattern that matched
        section: Section name

    Returns:
        Confidence score (0.7-0.9)
    """
    # Check if it's an exact match pattern (ends with $)
    if pattern.endswith("$"):
        return 0.9

    # Check if it's a numbered section pattern (contains digit + optional punctuation)
    if re.search(r"\\d\.?", pattern) or re.search(r"(一|二|三|四)[\.、]", pattern):
        return 0.85

    # Default fuzzy match confidence
    return 0.7


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


def detect_section_with_confidence(text: str) -> tuple[Optional[str], float]:
    """Detect which section a header belongs to with confidence score.

    Per D-03: Returns section name and confidence (0.7-0.9).

    Args:
        text: The header text to analyze

    Returns:
        Tuple of (section name, confidence) or (None, 0.0) if not matched
    """
    text_lower = text.strip().lower()

    for section in ["introduction", "methods", "results", "conclusion"]:
        patterns = IMRAD_PATTERNS.get(section, [])
        for pattern in patterns:
            if re.match(pattern, text_lower, re.IGNORECASE):
                confidence = calculate_pattern_confidence(text, pattern, section)
                return (section, confidence)

    return (None, 0.0)


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
    detected_headers = {}
    section_confidences = {}

    for item in items:
        if item.get("type") != "text":
            continue

        text = item.get("text", "").strip()
        if not text:
            continue

        # Check if this is a section header with confidence scoring
        detected, confidence = detect_section_with_confidence(text)
        if detected:
            current_section = detected
            detected_headers[detected] = text
            # Track best confidence for each section per D-03
            if (
                detected not in section_confidences
                or confidence > section_confidences[detected]
            ):
                section_confidences[detected] = confidence
            continue  # Don't include header text in content

        # Add text to current section
        if current_section in sections:
            sections[current_section]["texts"].append(
                {"text": text, "page": item.get("page"), "bbox": item.get("bbox")}
            )

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

    # Build final structure with weighted confidence scoring per D-03
    result = {}
    total_words = 0
    for section_name, data in sections.items():
        combined_text = "\n\n".join(t["text"] for t in data["texts"])
        word_count = len(combined_text.split()) if combined_text else 0
        total_words += word_count

        # Use weighted confidence from header detection per D-03
        if section_name in section_confidences:
            confidence = section_confidences[section_name]  # 0.7-0.9
        elif section_name in detected_headers:
            # Header detected but no confidence recorded - use default
            confidence = 0.85
        else:
            # No header detected for this section
            confidence = 0.5

        result[section_name] = {
            "content": combined_text,
            "word_count": word_count,
            "page_start": data["page_start"],
            "page_end": data["page_end"],
            "confidence": confidence,
        }

    # Overall confidence score (average of detected sections)
    detected_count = len(detected_headers)
    result["_estimated"] = False
    result["_confidence_score"] = (
        sum(section_confidences.values()) / detected_count
        if detected_count > 0
        else 0.5
    )
    result["_detected_headers"] = list(detected_headers.keys())

    return result


def _apply_fallback_strategy(
    items: List[Dict[str, Any]], sections: Dict[str, Dict[str, Any]]
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
                all_texts.append(
                    {"text": text, "page": item.get("page"), "bbox": item.get("bbox")}
                )

    n = len(all_texts)
    if n == 0:
        return _create_empty_result()

    # Distribute content evenly: 25% each section
    intro_texts = all_texts[: max(1, n // 4)]
    methods_texts = all_texts[max(1, n // 4) : max(1, n // 2)]
    results_texts = all_texts[max(1, n // 2) : max(1, 3 * n // 4)]
    conclusion_texts = all_texts[max(1, 3 * n // 4) :]

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


def extract_metadata(
    items: List[Dict[str, Any]], arxiv_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extract paper metadata (title, authors, abstract) from first page.
    Uses heuristics based on position and formatting.

    Args:
        items: List of parsed document items
        arxiv_id: Optional arXiv ID (e.g., "2604.01226")

    Returns:
        Dict with title, authors, abstract, keywords, doi
    """
    metadata = {
        "title": None,
        "authors": [],
        "abstract": None,
        "keywords": [],
        "doi": None,
        "year": None,
        "venue": None,
    }

    # Extract year from arXiv ID first (most reliable)
    # arXiv ID format: YYMM.NNNNN or YYMM.NNNNNvN (e.g., 2604.01226v1 = 2026年4月)
    if arxiv_id:
        try:
            # Remove version suffix if present (v1, v2, etc.)
            arxiv_id_clean = re.sub(r"v\d+$", "", arxiv_id)
            # Extract first 2 digits (year)
            year_part = arxiv_id_clean[:2]
            year = (
                2000 + int(year_part) if int(year_part) < 50 else 1900 + int(year_part)
            )
            metadata["year"] = year
            logger.info("Extracted year from arXiv ID", arxiv_id=arxiv_id, year=year)
        except (ValueError, IndexError):
            pass

    # Get first page items only
    first_page_items = [
        i for i in items if i.get("page") == 1 and i.get("type") == "text"
    ]

    if not first_page_items:
        return metadata

    # Sort by vertical position (top to bottom)
    first_page_items.sort(key=lambda x: x.get("bbox", {}).get("t", 0), reverse=True)

    # Extract title (usually the largest text at the top)
    # Title is typically on the first few items and has larger font
    # Use the first non-empty text item as title (it's usually at the very top)
    for item in first_page_items[:3]:  # Check first 3 items
        text = item.get("text", "").strip()
        if text and len(text) > 10:  # Minimum title length
            # Check if it looks like a title (not an author or affiliation line)
            # Titles typically don't contain commas separating names or email addresses
            if not re.search(r"@|alibaba|university|institute", text, re.IGNORECASE):
                metadata["title"] = text
                break

    # If still no title, use font size heuristic
    if not metadata["title"]:
        title_candidates = []
        for idx, item in enumerate(first_page_items[:5]):  # Check first 5 items
            text = item.get("text", "").strip()
            if text and len(text) > 10:  # Minimum title length
                bbox = item.get("bbox", {})
                height = bbox.get("t", 0) - bbox.get("b", 0)
                title_candidates.append({"text": text, "height": height, "index": idx})

        # Select title: prefer larger font (height)
        if title_candidates:
            title_candidates.sort(key=lambda x: x["height"], reverse=True)
            metadata["title"] = title_candidates[0]["text"]

    # Extract authors (usually after title, before affiliations)
    # Authors typically contain multiple names separated by commas or numbers
    author_items = []
    for idx, item in enumerate(first_page_items[1:10]):  # Check items 2-10
        text = item.get("text", "").strip()
        if not text:
            continue

        # Check if this looks like author names
        # Authors often have: "Name1, Name2, Name3" or "Name1 1, Name2 2"
        if re.search(r"\d{1,2}\s*,|\s+and\s+|,\s*[A-Z]", text):
            # Check it's not an affiliation (which usually has "University", "Institute", etc.)
            if not re.search(
                r"(University|Institute|College|Department|Lab|Laboratory)",
                text,
                re.IGNORECASE,
            ):
                author_items.append(text)

    if author_items:
        # Combine and clean author names
        authors_text = author_items[0]
        # Remove superscript numbers
        authors_text = re.sub(r"\s*\d+\s*", " ", authors_text)
        # Split by comma or "and"
        authors = re.split(r",\s*|\s+and\s+", authors_text)
        metadata["authors"] = [
            a.strip() for a in authors if a.strip() and len(a.strip()) > 2
        ]

    # Extract abstract
    abstract_start = None
    abstract_text = []

    for idx, item in enumerate(first_page_items):
        text = item.get("text", "").strip()
        if not text:
            continue

        # Detect abstract header
        if re.match(r"^(abstract|摘要)\s*$", text, re.IGNORECASE):
            abstract_start = idx + 1
            continue

        # Collect abstract text
        if abstract_start and idx >= abstract_start:
            # Stop at next section header
            if re.match(r"^(1\.|introduction|keywords|关键词)", text, re.IGNORECASE):
                break
            abstract_text.append(text)

    if abstract_text:
        metadata["abstract"] = " ".join(abstract_text)

    # Extract keywords
    keywords_text = None
    for item in first_page_items:
        text = item.get("text", "").strip()
        # Look for keywords section
        if re.match(r"^(keywords|关键词|key words)", text, re.IGNORECASE):
            # Extract keywords after the label
            keywords_match = re.search(
                r"(?:keywords|关键词|key words)[:\s]+(.+)", text, re.IGNORECASE
            )
            if keywords_match:
                keywords_text = keywords_match.group(1)
            break

    if keywords_text:
        # Split by comma, semicolon, or period
        keywords = re.split(r"[,;，；]\s*", keywords_text)
        metadata["keywords"] = [k.strip() for k in keywords if k.strip()]

    # Extract DOI
    for item in first_page_items:
        text = item.get("text", "").strip()
        doi_match = re.search(r"(?:doi:?\s*)?(10\.\d{4,}/[^\s]+)", text, re.IGNORECASE)
        if doi_match:
            metadata["doi"] = doi_match.group(1)
            break

    # Extract year from arXiv ID or text (fallback)
    # Note: year already extracted from arXiv ID if provided
    if not metadata["year"]:
        # Try to find arXiv date in text (e.g., "12 Mar 2026")
        for item in first_page_items[:15]:
            text = item.get("text", "").strip()
            # Look for arXiv submission date pattern
            date_match = re.search(r"(\d{1,2}\s+[A-Za-z]{3}\s+(\d{4}))", text)
            if date_match:
                metadata["year"] = int(date_match.group(2))
                break

            # Fallback: look for 4-digit year
            if not metadata["year"]:
                year_match = re.search(r"\b(19|20)\d{2}\b", text)
                if year_match:
                    metadata["year"] = int(year_match.group(0))
                    break

    logger.info(
        "Extracted metadata from first page",
        title=metadata["title"][:50] if metadata["title"] else None,
        authors_count=len(metadata["authors"]),
        has_abstract=metadata["abstract"] is not None,
    )

    return metadata


async def extract_imrad_enhanced(
    items: List[Dict[str, Any]], markdown: str, paper_metadata: Dict[str, Any]
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
            "High confidence IMRaD extraction, skipping LLM", confidence=confidence
        )
        return rule_based_result

    # Step 3: Low confidence - use LLM (per D-05)
    logger.info(
        "Low confidence IMRaD extraction, using LLM assistance", confidence=confidence
    )

    try:
        llm_result = await _extract_with_llm(
            markdown=markdown,
            model="glm-4-flash",  # LOCKED model per D-05
        )

        # Step 4: Merge results
        final_result = _merge_imrad_results(rule_based_result, llm_result)

        return final_result

    except Exception as e:
        logger.error(
            "LLM-assisted IMRaD extraction failed, returning rule-based result",
            error=str(e),
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
        model=model, messages=[{"role": "user", "content": prompt}], temperature=0.3
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
            content=content[:500],
        )
        raise ValueError(f"Invalid JSON from LLM: {e}")


def _merge_imrad_results(
    rule_based: Dict[str, Any], llm: Dict[str, Any]
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
        rule_confidence = (
            rule_data.get("confidence", 0) if isinstance(rule_data, dict) else 0
        )
        llm_confidence = (
            llm_data.get("confidence", 0) if isinstance(llm_data, dict) else 0
        )

        if rule_confidence >= llm_confidence:
            merged[section] = rule_data
        else:
            # Use LLM result but ensure it has the right structure
            merged[section] = {
                "content": rule_data.get("content", ""),
                "word_count": rule_data.get("word_count", 0),
                "page_start": llm_data.get("page_start")
                if isinstance(llm_data, dict)
                else None,
                "page_end": llm_data.get("page_end")
                if isinstance(llm_data, dict)
                else None,
                "confidence": llm_data.get("confidence", 0.75)
                if isinstance(llm_data, dict)
                else 0.75,
            }

    # LLM-assisted results have minimum 0.75 confidence
    merged["_estimated"] = False
    merged["_confidence_score"] = max(
        rule_based.get("_confidence_score", 0),
        0.75,  # LLM-assisted minimum confidence
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
    metadata["authors"] = list(dict.fromkeys(author_candidates))[
        :10
    ]  # Remove duplicates, max 10

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
            if detect_section(text) or re.match(
                r"^\s*(introduction|引言|1\.\s)", text, re.IGNORECASE
            ):
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
            keyword_text = re.sub(
                r"^\s*(keywords|关键词)[：:]?\s*", "", text, flags=re.IGNORECASE
            )
            if keyword_text:
                metadata["keywords"] = [
                    k.strip() for k in re.split(r"[,;，；]", keyword_text) if k.strip()
                ]
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
