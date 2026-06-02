"""Input validation for Milvus filter parameters.

Prevents filter injection by validating paper_id and section_path values.
"""

from __future__ import annotations

import re

# Valid paper_id pattern: alphanumeric, hyphens, underscores, dots
_PAPER_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\.]+$")
# Valid section_path pattern: alphanumeric, hyphens, underscores, dots, slashes
_SECTION_PATH_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\.\/]+$")
# Characters that could be used for Milvus filter injection
_INJECTION_CHARS = re.compile(r'[\"\'\\;(){}\[\]|&!<>]')


def validate_paper_id(paper_id: str) -> str:
    """Validate and return a safe paper_id for Milvus filter expressions.

    Args:
        paper_id: The paper ID to validate

    Returns:
        The validated paper_id

    Raises:
        ValueError: If the paper_id contains invalid characters
    """
    cleaned = str(paper_id or "").strip()
    if not cleaned:
        raise ValueError("paper_id cannot be empty")
    if len(cleaned) > 128:
        raise ValueError(f"paper_id too long: {len(cleaned)} > 128")
    if _INJECTION_CHARS.search(cleaned):
        raise ValueError(f"paper_id contains invalid characters: {cleaned!r}")
    if not _PAPER_ID_PATTERN.match(cleaned):
        raise ValueError(f"paper_id format invalid: {cleaned!r}")
    return cleaned


def validate_section_path(section_path: str) -> str:
    """Validate and return a safe section_path for Milvus filter expressions.

    Args:
        section_path: The section path to validate

    Returns:
        The validated section_path

    Raises:
        ValueError: If the section_path contains invalid characters
    """
    cleaned = str(section_path or "").strip().lower()
    if not cleaned:
        raise ValueError("section_path cannot be empty")
    if len(cleaned) > 256:
        raise ValueError(f"section_path too long: {len(cleaned)} > 256")
    if _INJECTION_CHARS.search(cleaned):
        raise ValueError(f"section_path contains invalid characters: {cleaned!r}")
    if not _SECTION_PATH_PATTERN.match(cleaned):
        raise ValueError(f"section_path format invalid: {cleaned!r}")
    return cleaned


def validate_user_id(user_id: str) -> str:
    """Validate and return a safe user_id for Milvus filter expressions.

    Args:
        user_id: The user ID to validate

    Returns:
        The validated user_id

    Raises:
        ValueError: If the user_id contains invalid characters
    """
    cleaned = str(user_id or "").strip()
    if not cleaned:
        raise ValueError("user_id cannot be empty")
    if len(cleaned) > 128:
        raise ValueError(f"user_id too long: {len(cleaned)} > 128")
    if _INJECTION_CHARS.search(cleaned):
        raise ValueError(f"user_id contains invalid characters: {cleaned!r}")
    # user_id allows alphanumeric, hyphens, underscores, dots, and @ for emails
    if not re.match(r"^[a-zA-Z0-9_\-\.@]+$", cleaned):
        raise ValueError(f"user_id format invalid: {cleaned!r}")
    return cleaned


def validate_paper_ids(paper_ids: list[str] | None) -> list[str]:
    """Validate a list of paper IDs, returning only valid ones.

    Args:
        paper_ids: List of paper IDs to validate

    Returns:
        List of validated paper IDs (invalid ones are silently dropped)
    """
    if not paper_ids:
        return []
    valid = []
    for pid in paper_ids:
        try:
            valid.append(validate_paper_id(pid))
        except ValueError:
            continue
    return valid


def validate_section_paths(section_paths: list[str] | None) -> list[str]:
    """Validate a list of section paths, returning only valid ones.

    Args:
        section_paths: List of section paths to validate

    Returns:
        List of validated section paths (invalid ones are silently dropped)
    """
    if not section_paths:
        return []
    valid = []
    for path in section_paths:
        try:
            valid.append(validate_section_path(path))
        except ValueError:
            continue
    return valid
