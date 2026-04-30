from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Optional

from app.models.paper import Paper, PaperChunk
from app.services.evidence_contract_service import build_citation_jump_url, load_chunk_index

_SLOT_ALIASES: dict[str, tuple[str, ...]] = {
    "research_question": ("abstract", "introduction", "background", "objective", "motivation"),
    "method": ("method", "methods", "approach", "architecture", "model"),
    "experiment": ("experiment", "experiments", "evaluation", "setup", "dataset"),
    "result": ("result", "results", "analysis", "finding", "findings"),
    "conclusion": ("conclusion", "conclusions", "discussion", "summary"),
    "limitation": ("limitation", "limitations", "future_work", "threats", "discussion"),
}

_SLOT_TITLES: dict[str, str] = {
    "research_question": "Research Question",
    "method": "Method",
    "experiment": "Experiment",
    "result": "Result",
    "conclusion": "Conclusion",
    "limitation": "Limitation",
}

_CONTENT_TYPES = {"text", "table", "figure", "caption", "formula", "page"}


def _normalize_section_path(value: Any) -> str:
    if not value:
        return ""
    return str(value).strip().lower().replace(" ", "_")



def _normalize_content_type(value: Any, *, is_table: bool = False, is_figure: bool = False, is_formula: bool = False) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in _CONTENT_TYPES:
        return normalized
    if is_table:
        return "table"
    if is_figure:
        return "figure"
    if is_formula:
        return "formula"
    return "text"



def _safe_text(value: Any, *, limit: int = 360) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return f"{text[: limit - 3].rstrip()}..."



def _build_evidence_block(record: dict[str, Any], paper_id: str) -> dict[str, Any]:
    source_chunk_id = str(record.get("source_chunk_id") or record.get("chunk_id") or record.get("id") or "")
    page_num = record.get("page_num") or record.get("page_start")
    if not isinstance(page_num, int):
        page_num = None
    section_path = _normalize_section_path(
        record.get("normalized_section_path") or record.get("section_path") or record.get("section")
    )
    content_type = _normalize_content_type(
        record.get("content_type"),
        is_table=bool(record.get("is_table") or record.get("isTable")),
        is_figure=bool(record.get("is_figure") or record.get("isFigure")),
        is_formula=bool(record.get("is_formula") or record.get("isFormula")),
    )
    text = _safe_text(record.get("text") or record.get("content") or record.get("anchor_text"), limit=800)
    evidence_id = str(record.get("evidence_id") or source_chunk_id)
    return {
        "evidence_id": evidence_id,
        "source_type": "paper",
        "paper_id": paper_id,
        "source_chunk_id": source_chunk_id,
        "page_num": page_num,
        "section_path": section_path or None,
        "content_type": content_type,
        "text": text,
        "score": record.get("score"),
        "rerank_score": record.get("rerank_score"),
        "support_status": record.get("support_status"),
        "citation_jump_url": str(
            record.get("citation_jump_url")
            or build_citation_jump_url(
                paper_id=paper_id,
                source_chunk_id=source_chunk_id or evidence_id,
                page_num=page_num,
            )
        ),
    }



def _record_sort_key(record: dict[str, Any]) -> tuple[int, int, int]:
    page_num = record.get("page_num") or record.get("page_start") or 0
    content_type = _normalize_content_type(
        record.get("content_type"),
        is_table=bool(record.get("is_table") or record.get("isTable")),
        is_figure=bool(record.get("is_figure") or record.get("isFigure")),
        is_formula=bool(record.get("is_formula") or record.get("isFormula")),
    )
    type_rank = {"text": 0, "table": 1, "figure": 2, "caption": 3, "formula": 4, "page": 5}.get(content_type, 9)
    text_len = len(str(record.get("text") or record.get("content") or ""))
    return (int(page_num), type_rank, -text_len)



def _select_slot_record(records: list[dict[str, Any]], slot: str) -> Optional[dict[str, Any]]:
    aliases = _SLOT_ALIASES[slot]
    exact_matches = [
        record
        for record in records
        if any(alias in _normalize_section_path(record.get("normalized_section_path") or record.get("section_path") or record.get("section")) for alias in aliases)
    ]
    if exact_matches:
        return sorted(exact_matches, key=_record_sort_key)[0]

    if slot == "limitation":
        result_records = [
            record
            for record in records
            if any(alias in _normalize_section_path(record.get("normalized_section_path") or record.get("section_path") or record.get("section")) for alias in _SLOT_ALIASES["result"])
        ]
        if result_records:
            return sorted(result_records, key=_record_sort_key)[-1]

    return None



def _build_slot_payload(slot: str, record: Optional[dict[str, Any]], paper_id: str) -> dict[str, Any]:
    if record is None:
        return {"title": _SLOT_TITLES[slot], "content": None, "evidence_blocks": []}

    evidence_block = _build_evidence_block(record, paper_id)
    content = _safe_text(record.get("text") or record.get("content") or record.get("anchor_text"), limit=280)
    return {
        "title": _SLOT_TITLES[slot],
        "content": content or None,
        "evidence_blocks": [evidence_block],
    }



def _build_key_evidence(records: list[dict[str, Any]], paper_id: str) -> list[dict[str, Any]]:
    candidates = sorted(records, key=_record_sort_key)[:3]
    items: list[dict[str, Any]] = []
    for index, record in enumerate(candidates, start=1):
        text = _safe_text(record.get("anchor_text") or record.get("text") or record.get("content"), limit=220)
        if not text:
            continue
        items.append(
            {
                "label": f"Evidence {index}",
                "content": text,
                "evidence_blocks": [_build_evidence_block(record, paper_id)],
            }
        )
    return items



def normalize_reading_card_source_records(records: Iterable[Any], paper_id: str) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for record in records:
        if isinstance(record, PaperChunk):
            normalized.append(
                {
                    "id": record.id,
                    "source_chunk_id": record.id,
                    "paper_id": paper_id,
                    "page_num": record.page_start,
                    "section_path": record.section,
                    "normalized_section_path": _normalize_section_path(record.section),
                    "content_type": _normalize_content_type(
                        None,
                        is_table=record.is_table,
                        is_figure=record.is_figure,
                        is_formula=record.is_formula,
                    ),
                    "text": record.content,
                    "anchor_text": record.content[:200],
                }
            )
            continue

        if not isinstance(record, dict):
            continue

        normalized_section_path = _normalize_section_path(
            record.get("normalized_section_path") or record.get("section_path") or record.get("section")
        )
        normalized.append(
            {
                **record,
                "paper_id": str(record.get("paper_id") or paper_id),
                "source_chunk_id": str(record.get("source_chunk_id") or record.get("chunk_id") or record.get("id") or ""),
                "page_num": record.get("page_num") or record.get("page_start"),
                "section_path": record.get("section_path") or record.get("section"),
                "normalized_section_path": normalized_section_path,
                "content_type": _normalize_content_type(
                    record.get("content_type"),
                    is_table=bool(record.get("is_table") or record.get("isTable")),
                    is_figure=bool(record.get("is_figure") or record.get("isFigure")),
                    is_formula=bool(record.get("is_formula") or record.get("isFormula")),
                ),
                "text": str(record.get("text") or record.get("content") or ""),
                "anchor_text": str(record.get("anchor_text") or record.get("text") or record.get("content") or "")[:200],
            }
        )

    return [record for record in normalized if record.get("text") and record.get("source_chunk_id")]



def build_reading_card_doc(*, paper_id: str, records: Iterable[Any]) -> dict[str, Any]:
    normalized_records = normalize_reading_card_source_records(records, paper_id)

    card = {
        slot: _build_slot_payload(slot, _select_slot_record(normalized_records, slot), paper_id)
        for slot in _SLOT_ALIASES
    }
    card["key_evidence"] = _build_key_evidence(normalized_records, paper_id)
    return card



def persist_generated_reading_card(paper: Paper, reading_card_doc: dict[str, Any]) -> None:
    paper.reading_card_doc = reading_card_doc



def get_artifact_records_for_paper(paper_id: str) -> list[dict[str, Any]]:
    return [
        payload
        for payload in load_chunk_index().values()
        if str(payload.get("paper_id") or "") == paper_id
    ]



def ensure_reading_card_doc(
    paper: Paper,
    *,
    records: Iterable[Any] | None = None,
) -> Optional[dict[str, Any]]:
    if paper.reading_card_doc:
        return paper.reading_card_doc

    source_records = list(records or [])
    if not source_records:
        source_records = get_artifact_records_for_paper(paper.id)
    if not source_records:
        return None

    card = build_reading_card_doc(paper_id=paper.id, records=source_records)
    persist_generated_reading_card(paper, card)
    return card
