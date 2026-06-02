"""Prompt assembly and text cleaning for RAG answer generation.

Extracted from main_path_service.py to keep the orchestration layer under 800 lines.
"""

from __future__ import annotations

import re
from typing import Any

from app.rag_v3.schemas import EvidenceCandidate
from app.utils.zhipu_client import ZhipuLLMClient
from app.rag_v3.runtime_binding import RUNTIME_PROFILE

_SUMMARY_PREFIX_RE = re.compile(r"^\[Paper Summary:[^\]]+\]\s*", re.IGNORECASE)
_BRACKET_METADATA_LINE_RE = re.compile(r"^\[[^\]]+\]\s*$", re.IGNORECASE)
_LOW_SIGNAL_COMPARE_PATTERNS = (
    re.compile(r"let'?s think step[- ]by[- ]step", re.IGNORECASE),
    re.compile(r"\bchain of thought\b", re.IGNORECASE),
    re.compile(r"GLYPH<\d+>", re.IGNORECASE),
)

# LLM prompt sanitization constants
_SNIPPET_MAX_LENGTH = 500
_CONTROL_CHAR_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def sanitize_snippet(text: str, *, max_length: int = _SNIPPET_MAX_LENGTH) -> str:
    """Sanitize a text snippet for safe inclusion in LLM prompts.

    - Strips control characters
    - Limits length
    - Wraps in <evidence> delimiter
    """
    cleaned = _CONTROL_CHAR_PATTERN.sub("", str(text or ""))
    cleaned = cleaned.strip()
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rstrip() + "..."
    return cleaned


def wrap_evidence(text: str) -> str:
    """Wrap sanitized text in <evidence>...</evidence> delimiters."""
    sanitized = sanitize_snippet(text)
    return f"<evidence>{sanitized}</evidence>"


def _clean_display_evidence_text(text: str, *, title: str | None = None) -> str:
    cleaned = str(text or "").replace("\r\n", "\n").strip()
    if not cleaned:
        return ""

    cleaned = _SUMMARY_PREFIX_RE.sub("", cleaned)
    cleaned = re.sub(r"GLYPH<\d+>", " ", cleaned)

    lines: list[str] = []
    normalized_title = (title or "").strip()
    for raw_line in cleaned.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if _BRACKET_METADATA_LINE_RE.match(line):
            continue
        if normalized_title and line == normalized_title:
            continue
        lines.append(line)

    collapsed = re.sub(r"\s+", " ", " ".join(lines)).strip()
    return collapsed


def _build_summary_display_text(summary_record: dict[str, Any]) -> str:
    text = (
        summary_record.get("paper_summary")
        or summary_record.get("abstract")
        or summary_record.get("method_summary")
        or summary_record.get("result_summary")
        or ""
    )
    return _clean_display_evidence_text(str(text or ""), title=str(summary_record.get("title") or ""))


def _is_low_signal_compare_candidate(candidate: EvidenceCandidate) -> bool:
    text = (candidate.anchor_text or "").strip()
    if not text:
        return True
    return any(pattern.search(text) for pattern in _LOW_SIGNAL_COMPARE_PATTERNS)


def _build_answer_generation_prompt(
    *,
    query: str,
    citations: list[dict[str, Any]],
    paper_summaries: list[dict[str, Any]] | None = None,
) -> tuple[str, str]:
    summary_lines: list[str] = []
    for index, summary in enumerate(paper_summaries or [], start=1):
        summary_lines.append(
            "\n".join(
                [
                    f"[Paper Summary {index}]",
                    f"paper_id: {summary.get('paper_id') or ''}",
                    f"title: {summary.get('title') or ''}",
                    f"abstract: {sanitize_snippet(summary.get('abstract') or '')}",
                    f"paper_summary: {sanitize_snippet(summary.get('paper_summary') or '')}",
                    f"method_summary: {sanitize_snippet(summary.get('method_summary') or '')}",
                    f"result_summary: {sanitize_snippet(summary.get('result_summary') or '')}",
                ]
            )
        )

    evidence_lines: list[str] = []
    for index, citation in enumerate(citations, start=1):
        section_path = citation.get("section_path") or "unknown"
        page_num = citation.get("page_num")
        score = citation.get("score")
        evidence_lines.append(
            "\n".join(
                [
                    f"[Evidence {index}]",
                    f"paper_id: {citation.get('paper_id') or ''}",
                    f"section: {section_path}",
                    f"page: {page_num if page_num is not None else 'unknown'}",
                    f"score: {score if score is not None else 'unknown'}",
                    f"text: {wrap_evidence(citation.get('text_preview') or citation.get('anchor_text') or '')}",
                ]
            )
        )

    system_prompt = (
        "你是 ScholarAI 的论文问答回答器。"
        "你必须只基于提供的证据回答，不要编造。"
        "优先输出简洁、结构化、直接回答用户问题的中文。"
        "如果证据不足，明确说明证据不足以及缺的是什么。"
        "如果问题是在问论文的贡献、创新、研究问题或动机，优先综合摘要、引言和贡献相关证据。"
    )
    user_prompt = (
        f"用户问题：{query}\n\n"
        "请基于以下证据回答。"
        "先直接回答问题，再给出 2-4 个要点；不要逐字复述原文；不要输出与问题无关的解释。\n\n"
        + ("\n\n".join(summary_lines) + "\n\n" if summary_lines else "")
        + "\n\n".join(evidence_lines)
    )
    return system_prompt, user_prompt


def _build_compare_answer_generation_prompt(
    *,
    query: str,
    citations: list[dict[str, Any]],
    paper_summaries: list[dict[str, Any]] | None = None,
) -> tuple[str, str]:
    summary_by_paper: dict[str, dict[str, Any]] = {
        str(item.get("paper_id") or ""): item
        for item in (paper_summaries or [])
        if str(item.get("paper_id") or "").strip()
    }

    evidence_by_paper: dict[str, list[dict[str, Any]]] = {}
    for citation in citations:
        paper_id = str(citation.get("paper_id") or "").strip()
        if not paper_id:
            continue
        evidence_by_paper.setdefault(paper_id, []).append(citation)

    paper_blocks: list[str] = []
    for index, paper_id in enumerate(evidence_by_paper.keys(), start=1):
        summary = summary_by_paper.get(paper_id, {})
        paper_evidence = evidence_by_paper.get(paper_id, [])
        first_evidence = paper_evidence[0] if paper_evidence else {}
        title = str(summary.get("title") or first_evidence.get("title") or paper_id)
        evidence_lines: list[str] = []
        for evidence in paper_evidence[:4]:
            section_path = str(evidence.get("section_path") or "unknown")
            snippet = str(evidence.get("text_preview") or evidence.get("anchor_text") or "").strip()
            if not snippet:
                continue
            evidence_lines.append(f"- [{section_path}] {sanitize_snippet(snippet)}")
        paper_blocks.append(
            "\n".join(
                [
                    f"[Paper {index}]",
                    f"paper_id: {paper_id}",
                    f"title: {title}",
                    f"summary: {sanitize_snippet(summary.get('paper_summary') or summary.get('abstract') or '')}",
                    "evidence:",
                    *evidence_lines,
                ]
            ).strip()
        )

    system_prompt = (
        "你是 ScholarAI 的跨论文比较回答器。"
        "你必须只根据提供的证据进行比较，不要补全不存在的共同点。"
        "输出中文，优先给出短而直接的比较结论。"
        "如果共同点证据弱，可以明确写\"当前证据下共同点有限\"，不要硬凑。"
        "如果只能回答局部差异，也要先给出已知差异，再说明证据缺口。"
        "下一步研究问题必须从已有证据推导，不要写空泛套话。"
    )
    user_prompt = (
        f"用户问题：{query}\n\n"
        "请基于以下按论文整理的证据进行比较回答。"
        "要求：\n"
        "1. 先给 1 句直接结论。\n"
        "2. 核心差异：优先列出证据最强的 2-3 条；每条都明确是哪篇论文的什么维度。\n"
        "3. 共同点：只写被两篇论文都支持的点；如果证据不够，明确写\"当前证据下共同点有限\"，并说明是哪些维度缺证据。\n"
        "4. 下一步研究问题：给 1-2 条，并明确是由哪篇论文的证据缺口或局限引出的。\n"
        "5. 不要为了凑结构写空话；如果只有差异有把握，就重点回答差异。\n\n"
        + "\n\n".join(paper_blocks)
    )
    return system_prompt, user_prompt


def _build_compare_answer_fallback(
    *,
    citations: list[dict[str, Any]],
    paper_summaries: list[dict[str, Any]] | None = None,
) -> str:
    summary_by_paper: dict[str, dict[str, Any]] = {
        str(item.get("paper_id") or ""): item
        for item in (paper_summaries or [])
        if str(item.get("paper_id") or "").strip()
    }
    evidence_by_paper: dict[str, list[dict[str, Any]]] = {}
    for citation in citations:
        paper_id = str(citation.get("paper_id") or "").strip()
        if not paper_id:
            continue
        evidence_by_paper.setdefault(paper_id, []).append(citation)

    if not evidence_by_paper:
        return "当前证据不足以形成可靠的跨论文比较。"

    paper_ids = list(evidence_by_paper.keys())
    paper_labels: dict[str, str] = {}
    for index, paper_id in enumerate(paper_ids, start=1):
        summary = summary_by_paper.get(paper_id, {})
        first_evidence = evidence_by_paper[paper_id][0] if evidence_by_paper[paper_id] else {}
        paper_labels[paper_id] = str(summary.get("title") or first_evidence.get("title") or f"论文{index}")

    difference_lines: list[str] = []
    known_sections: dict[str, set[str]] = {}
    for paper_id in paper_ids:
        label = paper_labels[paper_id]
        seen_sections: set[str] = set()
        known_sections[paper_id] = seen_sections
        for evidence in evidence_by_paper[paper_id]:
            section_path = str(evidence.get("section_path") or "unknown").strip() or "unknown"
            section_key = section_path.lower()
            if section_key in seen_sections:
                continue
            seen_sections.add(section_key)
            snippet = str(evidence.get("text_preview") or evidence.get("anchor_text") or "").strip()
            if not snippet:
                continue
            snippet = re.sub(r"\s+", " ", snippet)
            if len(snippet) > 120:
                snippet = f"{snippet[:117].rstrip()}..."
            difference_lines.append(f"- {label} 在 {section_path} 上的证据显示：{snippet}")
            if len(difference_lines) >= 4:
                break
        if len(difference_lines) >= 4:
            break

    common_sections = set.intersection(*(sections for sections in known_sections.values() if sections)) if all(known_sections.values()) else set()
    if common_sections:
        commonality_text = "共同点：当前证据显示两篇论文都覆盖了 " + "、".join(sorted(common_sections)[:3]) + " 等维度，但共同结论仍需要更直接的对应证据。"
    else:
        commonality_text = "共同点：当前证据下共同点有限，现有证据主要支持各自的方法、结果或局限，缺少一一对应的共同结论证据。"

    question_lines: list[str] = []
    for paper_id in paper_ids[:2]:
        label = paper_labels[paper_id]
        sections = sorted(known_sections.get(paper_id) or [])
        if "limitations" in sections:
            question_lines.append(f"- {label} 的 limitations 证据提示后续应继续验证其已知局限在其他任务或数据条件下是否仍成立。")
        elif "results" in sections:
            question_lines.append(f"- {label} 当前主要给出了 results 证据，后续需要补充其方法假设和失败案例，才能做更完整的横向比较。")
        elif "method" in sections or "methods" in sections:
            question_lines.append(f"- {label} 当前主要有方法层证据，后续需要补充与结果或局限直接对应的证据。")

    if not question_lines:
        question_lines.append("- 现有证据还需要补足同一维度上的成对证据，尤其是共同实验设置、局限和失败案例。")

    conclusion = "基于当前证据，可以先确认两篇论文在研究切入点或实现路径上存在差异，但共同点和完整优劣判断仍受证据覆盖限制。"
    parts = [
        conclusion,
        "",
        "核心差异：",
        *(difference_lines or ["- 当前证据主要是零散片段，只能确认比较证据尚不充分。"]),
        "",
        commonality_text,
        "",
        "下一步研究问题：",
        *question_lines[:2],
    ]
    return "\n".join(parts).strip()


async def generate_answer_from_citations(
    *,
    query: str,
    citations: list[dict[str, Any]],
    paper_summaries: list[dict[str, Any]] | None = None,
    query_family: str | None = None,
) -> str:
    from app.rag_v3.display_selector import is_compare_family

    if not citations:
        return "Insufficient evidence to answer confidently."

    if is_compare_family(query_family):
        system_prompt, user_prompt = _build_compare_answer_generation_prompt(
            query=query,
            citations=citations,
            paper_summaries=paper_summaries,
        )
    else:
        system_prompt, user_prompt = _build_answer_generation_prompt(
            query=query,
            citations=citations,
            paper_summaries=paper_summaries,
        )
    client = ZhipuLLMClient(model=RUNTIME_PROFILE.llm_model, max_tokens=900, temperature=0.2)
    content = await client.simple_completion(
        prompt=user_prompt,
        system_prompt=system_prompt,
        temperature=0.2,
    )
    answer_text = str(content or "").strip()
    if is_compare_family(query_family):
        if not answer_text or re.search(
            r"(insufficient evidence|证据不足|无法基于所提供的证据|无法根据提供的证据|cannot answer confidently)",
            answer_text,
            re.IGNORECASE,
        ):
            return _build_compare_answer_fallback(
                citations=citations,
                paper_summaries=paper_summaries,
            )
    return answer_text or "Insufficient evidence to answer confidently."
