"""Enhanced metadata extractor for academic papers

Provides sophisticated heuristics for extracting paper metadata:
- Title extraction using position, formatting, and heuristics
- Author extraction with pattern matching for names and affiliations
- Abstract extraction between Abstract header and next section
- Keywords extraction (comma or semicolon separated)
- DOI extraction (10.xxxx/xxxxx pattern)

This module extends the basic metadata extraction in imrad_extractor.py
with more sophisticated algorithms.
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class TextItem:
    """Represents a text item with provenance information."""
    text: str
    page: Optional[int] = None
    bbox: Optional[Dict[str, float]] = None
    font_size: Optional[float] = None
    is_bold: bool = False


class MetadataExtractor:
    """Enhanced metadata extractor with sophisticated heuristics."""

    # Patterns that suggest a text is NOT the title
    NON_TITLE_PATTERNS = [
        r"^\s*(abstract|摘要)\s*",
        r"^\s*(introduction|引言)\s*",
        r"^\s*(keywords|关键词)\s*",
        r"^\s*(doi|arxiv)\s*",
        r"^\s*figure\s*\d+",
        r"^\s*table\s*\d+",
        r"^\s*\d+\s*\.\s*",  # Numbered sections
        r"^\s*references?\s*",
        r"^\s*acknowledgments?\s*",
        r"@",  # Email addresses
    ]

    # Author name patterns
    AUTHOR_PATTERNS = [
        r"([A-Z][a-z]+\s+[A-Z][a-z]+)",  # "John Smith"
        r"([A-Z]\.\s*[A-Z][a-z]+)",  # "J. Smith"
        r"([A-Z][a-z]+,\s*[A-Z][a-z]+)",  # "Smith, John"
        r"([\u4e00-\u9fa5]{2,4})",  # Chinese names
    ]

    def __init__(self):
        self.non_title_regex = re.compile(
            "|".join(self.NON_TITLE_PATTERNS),
            re.IGNORECASE
        )

    def extract_title(self, items: List[Dict[str, Any]]) -> Optional[str]:
        """
        Extract paper title using multiple heuristics.

        Args:
            items: List of parsed document items

        Returns:
            Extracted title or None
        """
        # Get first page text items
        first_page_items = [
            TextItem(
                text=i.get("text", "").strip(),
                page=i.get("page"),
                bbox=i.get("bbox"),
            )
            for i in items
            if i.get("page") == 1 and i.get("type") == "text"
        ]

        if not first_page_items:
            return None

        candidates = []

        for idx, item in enumerate(first_page_items[:10]):  # Check first 10 items
            text = item.text

            # Skip empty or very short text
            if len(text) < 10:
                continue

            # Skip if matches non-title patterns
            if self.non_title_regex.search(text):
                continue

            # Calculate title score based on heuristics
            score = self._calculate_title_score(text, idx, item)

            if score > 0:
                candidates.append((score, text))

        if not candidates:
            return None

        # Sort by score descending and return best match
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]

    def _calculate_title_score(self, text: str, position: int, item: TextItem) -> float:
        """Calculate a relevance score for title candidates.

        Args:
            text: The text to score
            position: Position in document (0-indexed)
            item: TextItem with metadata

        Returns:
            Score between 0 and 1
        """
        score = 0.0

        # Length heuristic: titles are usually 30-150 characters
        length = len(text)
        if 30 <= length <= 150:
            score += 0.3
        elif 20 <= length <= 200:
            score += 0.2

        # Position heuristic: title usually appears early
        if position <= 2:
            score += 0.3
        elif position <= 5:
            score += 0.1

        # Content heuristics
        # Academic titles often contain technical terms
        academic_indicators = ["analysis", "study", "review", "approach", "method", "model"]
        if any(indicator in text.lower() for indicator in academic_indicators):
            score += 0.1

        # Capitalization heuristic: title case often indicates title
        words = text.split()
        if words:
            capitalized_ratio = sum(1 for w in words if w[0].isupper()) / len(words)
            if 0.3 <= capitalized_ratio <= 0.8:
                score += 0.2

        # Penalize very long text
        if length > 300:
            score -= 0.3

        return max(0.0, min(1.0, score))

    def extract_authors(self, items: List[Dict[str, Any]], title: Optional[str] = None) -> List[str]:
        """
        Extract author names using pattern matching.

        Args:
            items: List of parsed document items
            title: Already extracted title (to exclude from authors)

        Returns:
            List of author names
        """
        authors = []
        author_emails = []

        # Get first page items
        first_page_items = [
            i for i in items
            if i.get("page") == 1 and i.get("type") == "text"
        ]

        for item in first_page_items[:30]:  # Check first 30 items
            text = item.get("text", "").strip()

            # Skip title
            if text == title:
                continue

            # Extract emails first
            if "@" in text:
                email_match = re.search(r"[\w.-]+@[\w.-]+\.\w+", text)
                if email_match:
                    email = email_match.group(0)
                    # Try to extract name from before email
                    name_part = text.split("<")[0] if "<" in text else text.split(email)[0]
                    name_part = re.sub(r"[\d\*†‡§¶#]", "", name_part).strip()
                    if name_part and len(name_part) < 100:
                        author_emails.append(name_part)
                continue

            # Look for author patterns
            for pattern in self.AUTHOR_PATTERNS:
                matches = re.findall(pattern, text)
                for match in matches:
                    # Clean up the match
                    name = match.strip()
                    if len(name) > 3 and len(name) < 50:
                        # Avoid duplicates
                        if name not in authors:
                            authors.append(name)

            # Limit authors
            if len(authors) >= 15:
                break

        # Combine email-derived and pattern-matched authors
        all_authors = author_emails + [a for a in authors if a not in author_emails]

        # Clean up and deduplicate
        cleaned_authors = []
        for author in all_authors[:10]:
            # Remove affiliations and numbers
            cleaned = re.sub(r"\d+|\*|†|‡|§|¶|#", "", author).strip()
            if cleaned and cleaned not in cleaned_authors:
                cleaned_authors.append(cleaned)

        return cleaned_authors

    def extract_abstract(self, items: List[Dict[str, Any]]) -> Optional[str]:
        """
        Extract abstract text between Abstract header and next section.

        Args:
            items: List of parsed document items

        Returns:
            Extracted abstract text or None
        """
        abstract_started = False
        abstract_parts = []
        max_length = 3000  # Limit abstract length

        for item in items:
            if item.get("type") != "text":
                continue

            text = item.get("text", "").strip()
            if not text:
                continue

            # Check for Abstract header
            if not abstract_started:
                if re.match(r"^\s*(abstract|摘要)\s*[:：]?\s*", text, re.IGNORECASE):
                    abstract_started = True
                    # Extract any text after "Abstract:" on same line
                    remainder = re.sub(r"^\s*(abstract|摘要)\s*[:：]?\s*", "", text, flags=re.IGNORECASE)
                    if remainder:
                        abstract_parts.append(remainder)
                    continue
            else:
                # Check for end of abstract (next section header)
                if self._is_section_header(text) and len(abstract_parts) > 0:
                    break

                # Stop at keywords or introduction
                if re.match(r"^\s*(keywords|关键词|introduction|引言)\s*", text, re.IGNORECASE):
                    break

                # Add text to abstract
                if len(text) > 10:  # Skip very short fragments
                    abstract_parts.append(text)

                # Check length limit
                total_length = sum(len(p) for p in abstract_parts)
                if total_length >= max_length:
                    break

        if abstract_parts:
            return " ".join(abstract_parts)

        return None

    def _is_section_header(self, text: str) -> bool:
        """Check if text looks like a section header.

        Args:
            text: Text to check

        Returns:
            True if text appears to be a section header
        """
        section_patterns = [
            r"^\s*\d+\.\s+\w+",  # "1. Introduction"
            r"^\s*[IVX]+\.\s*\w+",  # "I. Introduction"
            r"^#+\s*\w+",  # Markdown headers
        ]
        return any(re.match(pattern, text) for pattern in section_patterns)

    def extract_keywords(self, items: List[Dict[str, Any]]) -> List[str]:
        """
        Extract keywords after Keywords header.

        Args:
            items: List of parsed document items

        Returns:
            List of keywords
        """
        keywords_started = False
        keyword_text = ""

        for item in items:
            if item.get("type") != "text":
                continue

            text = item.get("text", "").strip()
            if not text:
                continue

            # Check for Keywords header
            if not keywords_started:
                match = re.match(r"^\s*(keywords|关键词)\s*[:：]?\s*(.*)", text, re.IGNORECASE)
                if match:
                    keywords_started = True
                    remainder = match.group(2)
                    if remainder:
                        keyword_text = remainder
                    continue
            else:
                # Next item after keywords header
                if len(text) > 0 and not self._is_section_header(text):
                    keyword_text += " " + text
                break

        if keyword_text:
            # Split by common delimiters
            keywords = re.split(r"[,;，；]", keyword_text)
            return [k.strip() for k in keywords if k.strip() and len(k.strip()) < 50][:10]

        return []

    def extract_doi(self, items: List[Dict[str, Any]]) -> Optional[str]:
        """
        Extract DOI using pattern matching.

        Args:
            items: List of parsed document items

        Returns:
            DOI string or None
        """
        doi_pattern = r"10\.\d{4,}(?:\.\d+)*/[^\s\"<>]+"

        for item in items:
            if item.get("type") != "text":
                continue

            text = item.get("text", "").strip()

            # Look for DOI pattern
            match = re.search(doi_pattern, text)
            if match:
                doi = match.group(0)
                # Clean up common suffixes
                doi = re.sub(r"[;,.]$", "", doi)
                return doi

        return None

    def extract_journal_info(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract journal/conference information from header/footer.

        Args:
            items: List of parsed document items

        Returns:
            Dict with journal, year, volume, pages
        """
        info = {
            "journal": None,
            "year": None,
            "volume": None,
            "pages": None,
        }

        # Check first few items for journal info
        for item in items[:20]:
            if item.get("type") != "text":
                continue

            text = item.get("text", "").strip()

            # Journal patterns
            journal_patterns = [
                r"Proceedings of\s+(.+)",
                r"Journal of\s+(.+)",
                r"IEEE\s+(.+)",
                r"ACM\s+(.+)",
            ]
            for pattern in journal_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    info["journal"] = match.group(0)
                    break

            # Year pattern
            year_match = re.search(r"\b(19|20)\d{2}\b", text)
            if year_match:
                info["year"] = int(year_match.group(0))

            # Volume pattern
            volume_match = re.search(r"Vol\.?\s*(\d+)", text, re.IGNORECASE)
            if volume_match:
                info["volume"] = volume_match.group(1)

        return info


def extract_title(items: List[Dict[str, Any]]) -> Optional[str]:
    """Convenience function to extract title."""
    extractor = MetadataExtractor()
    return extractor.extract_title(items)


def extract_authors(items: List[Dict[str, Any]], title: Optional[str] = None) -> List[str]:
    """Convenience function to extract authors."""
    extractor = MetadataExtractor()
    return extractor.extract_authors(items, title)


def extract_abstract(items: List[Dict[str, Any]]) -> Optional[str]:
    """Convenience function to extract abstract."""
    extractor = MetadataExtractor()
    return extractor.extract_abstract(items)


def extract_keywords(items: List[Dict[str, Any]]) -> List[str]:
    """Convenience function to extract keywords."""
    extractor = MetadataExtractor()
    return extractor.extract_keywords(items)


def extract_doi(items: List[Dict[str, Any]]) -> Optional[str]:
    """Convenience function to extract DOI."""
    extractor = MetadataExtractor()
    return extractor.extract_doi(items)


def extract_all_metadata(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Extract all metadata in one call.

    Args:
        items: List of parsed document items

    Returns:
        Dict with all metadata fields
    """
    extractor = MetadataExtractor()

    title = extractor.extract_title(items)
    authors = extractor.extract_authors(items, title)
    abstract = extractor.extract_abstract(items)
    keywords = extractor.extract_keywords(items)
    doi = extractor.extract_doi(items)
    journal_info = extractor.extract_journal_info(items)

    return {
        "title": title,
        "authors": authors,
        "abstract": abstract,
        "keywords": keywords,
        "doi": doi,
        **journal_info,
    }
