"""Notes API endpoints with Notes 2.0 evidence persistence."""

from typing import Any, List, Literal, Optional
import json
import re

from fastapi import APIRouter, HTTPException, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.orm_note import Note
from app.models.paper import Paper, PaperChunk
from app.core.notes_generator import NotesGenerator
from app.services.reading_notes_service import (
    build_generated_notes_payload,
    persist_generated_reading_notes,
)
from app.services.evidence_contract_service import (
    build_citation_jump_url,
    find_best_evidence_source_payload,
    get_evidence_source_payload,
)
from app.utils.logger import logger
from app.deps import CurrentUserId
from app.utils.problem_detail import Errors

router = APIRouter()
notes_generator = NotesGenerator()
SYSTEM_AI_NOTE_TAG = "__ai_note__"
DEFAULT_NOTE_SOURCE_TYPE = "manual"
NOTE_SOURCE_TYPES = {"manual", "chat", "read", "search", "compare", "review"}
SNAPSHOT_PAGE_RE = re.compile(r"^\[Page:(?P<page>\d+)\]\s*$", re.IGNORECASE)
NOTE_TITLE_PREFIX_RE = re.compile(r"^(Evidence|Claim)\s*:\s*", re.IGNORECASE)


def _empty_editor_document() -> dict[str, Any]:
    return {"type": "doc", "content": []}


def _text_to_editor_document(text: str) -> dict[str, Any]:
    return {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": text}] if text else [],
            }
        ],
    }


def _is_editor_document(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and value.get("type") == "doc"
        and isinstance(value.get("content"), list)
    )


def _normalize_content_doc(
    content_doc: Optional[dict[str, Any]],
    legacy_content: Optional[str],
) -> dict[str, Any]:
    if _is_editor_document(content_doc):
        return content_doc

    if isinstance(legacy_content, str) and legacy_content.strip():
        try:
            parsed = json.loads(legacy_content)
        except json.JSONDecodeError:
            return _text_to_editor_document(legacy_content)

        if _is_editor_document(parsed):
            return parsed

    if isinstance(legacy_content, str):
        return _text_to_editor_document(legacy_content)

    return _empty_editor_document()


def _extract_plain_text_from_doc(value: Any) -> str:
    doc = _normalize_content_doc(value if isinstance(value, dict) else None, value if isinstance(value, str) else "")
    texts: list[str] = []

    def walk(nodes: list[Any]) -> None:
        for node in nodes:
            if isinstance(node, dict):
                text = node.get("text")
                if isinstance(text, str) and text.strip():
                    texts.append(text)
                content = node.get("content")
                if isinstance(content, list):
                    walk(content)

    walk(doc.get("content", []))
    return "\n".join(part.strip() for part in texts if part.strip()).strip()


def _normalize_note_source_type(value: Optional[str]) -> str:
    candidate = (value or DEFAULT_NOTE_SOURCE_TYPE).strip().lower()
    return candidate if candidate in NOTE_SOURCE_TYPES else DEFAULT_NOTE_SOURCE_TYPE


def _normalize_note_title_text(value: Optional[str]) -> str:
    title = NOTE_TITLE_PREFIX_RE.sub("", (value or "").strip()).strip()
    return re.sub(r"\s+", " ", title)


def _build_evidence_note_title(claim: str) -> str:
    normalized = _normalize_note_title_text(claim)
    if len(normalized) <= 80:
        return normalized
    return normalized[:77].rstrip() + "..."


def _normalize_linked_evidence(value: Optional[list[dict[str, Any]]]) -> list[dict[str, Any]]:
    return [item for item in (value or []) if isinstance(item, dict)]


def _extract_snapshot_page_num(text: str) -> int | None:
    for raw_line in text.splitlines():
        line = raw_line.strip()
        match = SNAPSHOT_PAGE_RE.match(line)
        if match:
            try:
                return int(match.group("page"))
            except (TypeError, ValueError):
                return None
    return None


def _normalize_snapshot_text(text: str) -> str:
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            continue
        if line.startswith("Claim: "):
            continue
        if line.startswith("Paper: "):
            continue
        if line.startswith("Page: "):
            continue
        if line.startswith("Section: "):
            continue
        if line.startswith("Comment: "):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def _build_paper_chunk_payload(chunk: PaperChunk) -> dict[str, Any]:
    page_num = chunk.page_start or chunk.page_end
    if chunk.is_table:
        content_type = "table"
    elif chunk.is_figure:
        content_type = "figure"
    elif chunk.is_formula:
        content_type = "formula"
    else:
        content_type = "text"

    citation_jump_url = build_citation_jump_url(
        paper_id=chunk.paper_id,
        source_chunk_id=chunk.id,
        page_num=page_num,
    )
    return {
        "evidence_id": chunk.id,
        "source_type": "paper",
        "source_chunk_id": chunk.id,
        "paper_id": chunk.paper_id,
        "page_num": page_num,
        "section_path": chunk.section,
        "content_type": content_type,
        "content": chunk.content or "",
        "citation_jump_url": citation_jump_url,
        "read_url": citation_jump_url,
    }


async def _find_best_evidence_source_payload_db(
    db: AsyncSession,
    *,
    source_chunk_id: str | None = None,
    paper_id: str | None = None,
    section_path: str | None = None,
    page_num: int | None = None,
    text: str | None = None,
) -> dict[str, Any] | None:
    normalized_source_chunk_id = str(source_chunk_id or "").strip()
    if normalized_source_chunk_id.startswith("chunk_"):
        exact_result = await db.execute(
            select(PaperChunk).where(PaperChunk.id == normalized_source_chunk_id).limit(1)
        )
        exact_chunk = exact_result.scalar_one_or_none()
        if exact_chunk:
            return _build_paper_chunk_payload(exact_chunk)

    normalized_paper_id = str(paper_id or "").strip()
    if not normalized_paper_id:
        return None

    result = await db.execute(
        select(PaperChunk)
        .where(PaperChunk.paper_id == normalized_paper_id)
        .order_by(PaperChunk.page_start, PaperChunk.id)
    )
    chunks = list(result.scalars().all())
    if not chunks:
        return None

    normalized_section = str(section_path or "").strip().lower()
    raw_text = str(text or "").strip()
    normalized_text = _normalize_snapshot_text(raw_text)
    normalized_page = page_num if isinstance(page_num, int) and page_num > 0 else None
    if normalized_page is None and raw_text:
        normalized_page = _extract_snapshot_page_num(raw_text)

    best_payload: dict[str, Any] | None = None
    best_score = -1
    best_content_len = -1

    for chunk in chunks:
        score = 0
        chunk_section = str(chunk.section or "").strip().lower()
        chunk_page = chunk.page_start or chunk.page_end
        chunk_content = str(chunk.content or "").strip()

        if normalized_section:
            if chunk_section == normalized_section:
                score += 4
            elif chunk_section and (
                normalized_section in chunk_section or chunk_section in normalized_section
            ):
                score += 2

        if normalized_page and isinstance(chunk_page, int):
            if chunk_page == normalized_page:
                score += 3
            elif abs(chunk_page - normalized_page) == 1:
                score += 1

        if normalized_text and chunk_content:
            if normalized_text == chunk_content:
                score += 8
            elif normalized_text in chunk_content or chunk_content in normalized_text:
                score += 6
            else:
                left = normalized_text[:220]
                right = chunk_content[:220]
                if left and right and (left in right or right in left):
                    score += 4

        if score <= 0:
            continue

        content_len = len(chunk_content)
        if score > best_score or (score == best_score and content_len > best_content_len):
            best_payload = _build_paper_chunk_payload(chunk)
            best_score = score
            best_content_len = content_len

    return best_payload


async def _canonicalize_linked_evidence_item(
    item: dict[str, Any],
    db: AsyncSession | None = None,
) -> dict[str, Any]:
    canonical = find_best_evidence_source_payload(
        source_chunk_id=str(item.get("source_chunk_id") or "") or None,
        paper_id=str(item.get("paper_id") or "") or None,
        section_path=str(item.get("section_path") or "") or None,
        page_num=item.get("page_num") if isinstance(item.get("page_num"), int) else None,
        text=str(item.get("text") or "") or None,
    )
    if not canonical and db is not None:
        canonical = await _find_best_evidence_source_payload_db(
            db,
            source_chunk_id=str(item.get("source_chunk_id") or "") or None,
            paper_id=str(item.get("paper_id") or "") or None,
            section_path=str(item.get("section_path") or "") or None,
            page_num=item.get("page_num") if isinstance(item.get("page_num"), int) else None,
            text=str(item.get("text") or "") or None,
        )
    if not canonical:
        fallback_source_chunk_id = str(
            item.get("source_chunk_id") or item.get("evidence_id") or ""
        )
        fallback_paper_id = str(item.get("paper_id") or "")
        fallback_page_num = item.get("page_num") if isinstance(item.get("page_num"), int) else None
        citation_jump_url = str(item.get("citation_jump_url") or "")
        if not citation_jump_url and fallback_paper_id and fallback_source_chunk_id:
            citation_jump_url = build_citation_jump_url(
                paper_id=fallback_paper_id,
                source_chunk_id=fallback_source_chunk_id,
                page_num=fallback_page_num,
                source="evidence",
            )
        return {
            **item,
            "source_chunk_id": fallback_source_chunk_id,
            "evidence_id": str(item.get("evidence_id") or fallback_source_chunk_id),
            "citation_jump_url": citation_jump_url,
        }

    page_num = canonical.get("page_num")
    if not isinstance(page_num, int):
        page_num = item.get("page_num") if isinstance(item.get("page_num"), int) else None

    return {
        **item,
        "evidence_id": str(item.get("evidence_id") or canonical.get("evidence_id") or canonical.get("source_chunk_id") or ""),
        "source_type": str(item.get("source_type") or canonical.get("source_type") or "paper"),
        "paper_id": str(item.get("paper_id") or canonical.get("paper_id") or ""),
        "source_chunk_id": str(canonical.get("source_chunk_id") or item.get("source_chunk_id") or item.get("evidence_id") or ""),
        "page_num": page_num,
        "section_path": str(item.get("section_path") or canonical.get("section_path") or ""),
        "content_type": str(item.get("content_type") or canonical.get("content_type") or "text"),
        "text": str(item.get("text") or canonical.get("content") or canonical.get("quote_text") or canonical.get("anchor_text") or ""),
        "citation_jump_url": str(
            canonical.get("citation_jump_url")
            or item.get("citation_jump_url")
            or ""
        ),
        }


async def _canonicalize_linked_evidence(
    items: list[dict[str, Any]],
    db: AsyncSession | None = None,
) -> list[dict[str, Any]]:
    return [await _canonicalize_linked_evidence_item(item, db) for item in items]


def _build_note_body_snapshot(
    *,
    claim: str,
    evidence_block: dict[str, Any],
    user_comment: Optional[str] = None,
) -> dict[str, Any]:
    body_text = str(evidence_block.get("text") or "").strip() or claim.strip()
    lines = [body_text]
    if user_comment:
        lines.extend(["", user_comment.strip()])

    return _text_to_editor_document("\n".join(lines).strip())


def _should_append_evidence_snapshot_to_note(target_note_id: Optional[str]) -> bool:
    """Append machine snapshot text only for standalone evidence notes."""
    return not bool(target_note_id)


def _append_document_content(
    existing_doc: Optional[dict[str, Any]],
    addition_doc: dict[str, Any],
    legacy_content: Optional[str] = None,
) -> dict[str, Any]:
    base_doc = _normalize_content_doc(existing_doc, legacy_content)
    return {
        "type": "doc",
        "content": [
            *(base_doc.get("content", []) or []),
            *(addition_doc.get("content", []) or []),
        ],
    }


def _persist_note_content(
    note: Note,
    *,
    content: Optional[str],
    content_doc: Optional[dict[str, Any]],
) -> None:
    normalized_doc = _normalize_content_doc(content_doc, content)
    note.content_doc = normalized_doc
    note.content = _extract_plain_text_from_doc(normalized_doc)


# =============================================================================
# Request/Response Models
# =============================================================================


class NoteCreate(BaseModel):
    """Request to create a note."""

    title: str = Field(..., min_length=1, max_length=500)
    content: Optional[str] = None
    contentDoc: Optional[dict[str, Any]] = Field(default=None, alias="contentDoc")
    linkedEvidence: List[dict[str, Any]] = Field(default_factory=list, alias="linkedEvidence")
    sourceType: Optional[str] = Field(default=None, alias="sourceType")
    tags: List[str] = Field(default=[])
    paperIds: List[str] = Field(default=[], alias="paperIds")

    class Config:
        populate_by_name = True


class NoteUpdate(BaseModel):
    """Request to update a note."""

    title: Optional[str] = Field(None, min_length=1, max_length=500)
    content: Optional[str] = None
    contentDoc: Optional[dict[str, Any]] = Field(default=None, alias="contentDoc")
    linkedEvidence: Optional[List[dict[str, Any]]] = Field(default=None, alias="linkedEvidence")
    sourceType: Optional[str] = Field(default=None, alias="sourceType")
    tags: Optional[List[str]] = None
    paperIds: Optional[List[str]] = Field(None, alias="paperIds")

    class Config:
        populate_by_name = True


class NoteResponse(BaseModel):
    """Response wrapper for note endpoints."""

    success: bool = True
    data: dict


class NotesListResponse(BaseModel):
    """Response wrapper for notes list."""

    success: bool = True
    data: dict


# =============================================================================
# Helper Functions
# =============================================================================


def _format_note_response(note: Note) -> dict:
    """Format note for API response with camelCase fields."""
    content_doc = _normalize_content_doc(note.content_doc, note.content)
    return {
        "id": note.id,
        "userId": note.user_id,
        "title": _normalize_note_title_text(note.title),
        "content": note.content,
        "contentDoc": content_doc,
        "linkedEvidence": _normalize_linked_evidence(note.linked_evidence),
        "sourceType": _normalize_note_source_type(note.source_type),
        "tags": note.tags or [],
        "paperIds": note.paper_ids or [],
        "createdAt": note.created_at.isoformat() if note.created_at else None,
        "updatedAt": note.updated_at.isoformat() if note.updated_at else None,
    }


async def _format_note_response_async(note: Note, db: AsyncSession) -> dict:
    payload = _format_note_response(note)
    payload["linkedEvidence"] = await _canonicalize_linked_evidence(
        _normalize_linked_evidence(note.linked_evidence),
        db,
    )
    return payload


def _sanitize_note_tags(tags: Optional[List[str]]) -> List[str]:
    """Strip system-only tags from user-editable note payloads."""
    return [tag for tag in (tags or []) if tag != SYSTEM_AI_NOTE_TAG]


def _is_system_ai_note(tags: Optional[List[str]]) -> bool:
    """Detect legacy AI note records that should be hidden from note CRUD boundaries."""
    return SYSTEM_AI_NOTE_TAG in (tags or [])


def _sort_notes(notes: List[Note], sort_by: str, order: str) -> List[Note]:
    """Sort notes in Python to avoid dialect-specific ARRAY operators in dev envs."""
    sort_key = {
        "createdAt": lambda note: note.created_at,
        "created_at": lambda note: note.created_at,
        "updatedAt": lambda note: note.updated_at,
        "updated_at": lambda note: note.updated_at,
        "title": lambda note: (note.title or "").lower(),
    }.get(sort_by, lambda note: note.created_at)

    return sorted(notes, key=sort_key, reverse=order == "desc")


class GenerateNotesRequest(BaseModel):
    """Request to generate notes for a paper."""

    paper_id: str = Field(..., alias="paperId")

    class Config:
        populate_by_name = True


class RegenerateNotesRequest(BaseModel):
    """Request to regenerate notes with modification."""

    paper_id: str = Field(..., alias="paperId")
    modification_request: str = Field(..., alias="modificationRequest")

    class Config:
        populate_by_name = True


class GeneratedNotesResponse(BaseModel):
    """Response wrapper for generated notes."""

    success: bool = True
    data: dict


class EvidenceBlockPayload(BaseModel):
    evidence_id: str = Field(..., min_length=1, alias="evidence_id")
    source_type: Literal["paper", "note", "web", "user_upload"] = Field(
        default="paper", alias="source_type"
    )
    paper_id: str = Field(..., min_length=1, alias="paper_id")
    source_chunk_id: str = Field(..., min_length=1, alias="source_chunk_id")
    page_num: Optional[int] = Field(default=None, alias="page_num")
    section_path: Optional[str] = Field(default=None, alias="section_path")
    content_type: str = Field(default="text", alias="content_type")
    text: str = Field(default="")
    score: Optional[float] = None
    rerank_score: Optional[float] = Field(default=None, alias="rerank_score")
    support_status: Optional[str] = Field(default=None, alias="support_status")
    citation_jump_url: Optional[str] = Field(default=None, alias="citation_jump_url")

    class Config:
        populate_by_name = True


class EvidenceNoteCreate(BaseModel):
    claim: str = Field(..., min_length=1)
    evidence_block: EvidenceBlockPayload = Field(..., alias="evidence_block")
    target_note_id: Optional[str] = Field(default=None, alias="target_note_id")
    surface: Literal["chat", "read", "search", "compare", "review"]
    user_comment: Optional[str] = Field(default=None, alias="user_comment")

    class Config:
        populate_by_name = True


# =============================================================================
# CRUD Endpoints
# =============================================================================


@router.post("", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
async def create_note(
    request: NoteCreate,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """Create a new note.

    Supports cross-paper association via paperIds array.
    """
    try:
        note = Note(
            user_id=user_id,
            title=request.title,
            source_type=_normalize_note_source_type(request.sourceType),
            tags=_sanitize_note_tags(request.tags),
            paper_ids=request.paperIds,
            linked_evidence=_normalize_linked_evidence(request.linkedEvidence),
        )
        _persist_note_content(
            note,
            content=request.content,
            content_doc=request.contentDoc,
        )

        db.add(note)
        await db.flush()
        await db.refresh(note)

        logger.info("Note created", note_id=note.id, user_id=user_id)

        return NoteResponse(success=True, data=await _format_note_response_async(note, db))

    except Exception as e:
        logger.error("Failed to create note", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to create note: {str(e)}"),
        )


@router.get("", response_model=NotesListResponse)
async def list_notes(
    paperId: Optional[str] = Query(None, description="Filter by paper ID"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    sortBy: str = Query("createdAt", description="Sort field"),
    order: str = Query("desc", description="Sort order (asc/desc)"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """List notes with optional filtering.

    Supports filtering by paperId (notes associated with specific paper) and tag.
    """
    try:
        result = await db.execute(select(Note).where(Note.user_id == user_id))
        notes = [
            note
            for note in result.scalars().all()
            if not _is_system_ai_note(note.tags)
            and (not paperId or paperId in (note.paper_ids or []))
            and (not tag or tag in (note.tags or []))
        ]

        total = len(notes)
        notes = _sort_notes(notes, sortBy, order)
        notes = notes[offset : offset + limit]

        return NotesListResponse(
            success=True,
            data={
                "notes": [await _format_note_response_async(n, db) for n in notes],
                "total": total,
                "limit": limit,
                "offset": offset,
            },
        )

    except Exception as e:
        logger.error("Failed to list notes", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to list notes: {str(e)}"),
        )


@router.get("/{note_id}", response_model=NoteResponse)
async def get_note(
    note_id: str, user_id: str = CurrentUserId, db: AsyncSession = Depends(get_db)
):
    """Get a specific note by ID."""
    try:
        result = await db.execute(
            select(Note).where(Note.id == note_id, Note.user_id == user_id)
        )
        note = result.scalar_one_or_none()

        if not note or _is_system_ai_note(note.tags):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found("Note not found"),
            )

        return NoteResponse(success=True, data=await _format_note_response_async(note, db))

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get note", error=str(e), note_id=note_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to get note: {str(e)}"),
        )


@router.put("/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: str,
    request: NoteUpdate,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """Update a note."""
    try:
        # Find note
        result = await db.execute(
            select(Note).where(Note.id == note_id, Note.user_id == user_id)
        )
        note = result.scalar_one_or_none()

        if not note or _is_system_ai_note(note.tags):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found("Note not found"),
            )

        # Update fields
        if request.title is not None:
            note.title = request.title
        if request.content is not None or request.contentDoc is not None:
            _persist_note_content(
                note,
                content=request.content,
                content_doc=request.contentDoc,
            )
        if request.tags is not None:
            note.tags = _sanitize_note_tags(request.tags)
        if request.paperIds is not None:
            note.paper_ids = request.paperIds
        if request.linkedEvidence is not None:
            note.linked_evidence = _normalize_linked_evidence(request.linkedEvidence)
        if request.sourceType is not None:
            note.source_type = _normalize_note_source_type(request.sourceType)

        await db.flush()
        await db.refresh(note)

        logger.info("Note updated", note_id=note_id, user_id=user_id)

        return NoteResponse(success=True, data=await _format_note_response_async(note, db))

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update note", error=str(e), note_id=note_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to update note: {str(e)}"),
        )


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: str, user_id: str = CurrentUserId, db: AsyncSession = Depends(get_db)
):
    """Delete a note."""
    try:
        # Find note
        result = await db.execute(
            select(Note).where(Note.id == note_id, Note.user_id == user_id)
        )
        note = result.scalar_one_or_none()

        if not note or _is_system_ai_note(note.tags):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found("Note not found"),
            )

        await db.delete(note)
        logger.info("Note deleted", note_id=note_id, user_id=user_id)

        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete note", error=str(e), note_id=note_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to delete note: {str(e)}"),
        )


@router.get("/paper/{paper_id}", response_model=NotesListResponse)
async def get_notes_by_paper(
    paper_id: str, user_id: str = CurrentUserId, db: AsyncSession = Depends(get_db)
):
    """Get notes for a specific paper (legacy endpoint)."""
    try:
        result = await db.execute(select(Note).where(Note.user_id == user_id))
        notes = [
            note
            for note in result.scalars().all()
            if not _is_system_ai_note(note.tags) and paper_id in (note.paper_ids or [])
        ]
        notes = _sort_notes(notes, "createdAt", "desc")

        return NotesListResponse(
            success=True,
            data={
                "notes": [await _format_note_response_async(n, db) for n in notes],
                "total": len(notes),
            },
        )

    except Exception as e:
        logger.error("Failed to get notes by paper", error=str(e), paper_id=paper_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to get notes: {str(e)}"),
        )


# =============================================================================
# AI-Generated Notes Endpoints
# =============================================================================


@router.post(
    "/generate",
    response_model=GeneratedNotesResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_notes(
    request: GenerateNotesRequest,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """Generate reading notes for a paper using AI.

    This uses the existing NotesGenerator to create AI-powered reading notes.
    """
    try:
        # Fetch paper data using SQLAlchemy
        result = await db.execute(select(Paper).where(Paper.id == request.paper_id))
        paper = result.scalar_one_or_none()

        if not paper:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found("Paper not found"),
            )

        imrad_data = paper.imrad_json
        if not imrad_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=Errors.validation("Paper not yet parsed"),
            )

        # Parse imrad_json if it's a string
        if isinstance(imrad_data, str):
            imrad_data = json.loads(imrad_data)

        # Prepare metadata
        paper_metadata = {
            "title": paper.title or "Unknown",
            "authors": paper.authors if paper.authors else [],
            "year": str(paper.year) if paper.year else "",
            "venue": paper.venue or "",
        }

        # Generate notes
        notes = await notes_generator.generate_notes(
            paper_metadata=paper_metadata, imrad_structure=imrad_data
        )

        # Update paper with new notes using SQLAlchemy
        new_version = persist_generated_reading_notes(paper, notes)
        await db.flush()
        await db.refresh(paper)

        logger.info("Notes generated", paper_id=request.paper_id, version=new_version)

        return GeneratedNotesResponse(
            success=True,
            data=build_generated_notes_payload(
                paper_id=request.paper_id,
                notes=notes,
                version=new_version,
            ),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to generate notes", error=str(e), paper_id=request.paper_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to generate notes: {str(e)}"),
        )


@router.post("/regenerate", response_model=GeneratedNotesResponse)
async def regenerate_notes(
    request: RegenerateNotesRequest,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """Regenerate reading notes with modification request."""
    try:
        # Fetch paper data using SQLAlchemy
        result = await db.execute(select(Paper).where(Paper.id == request.paper_id))
        paper = result.scalar_one_or_none()

        if not paper:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found("Paper not found"),
            )

        imrad_data = paper.imrad_json
        if not imrad_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=Errors.validation("Paper not yet parsed"),
            )

        # Parse imrad_json if it's a string
        if isinstance(imrad_data, str):
            imrad_data = json.loads(imrad_data)

        # Prepare metadata
        paper_metadata = {
            "title": paper.title or "Unknown",
            "authors": paper.authors if paper.authors else [],
            "year": str(paper.year) if paper.year else "",
            "venue": paper.venue or "",
        }

        # Regenerate notes with modification request
        notes = await notes_generator.regenerate_notes(
            paper_metadata=paper_metadata,
            imrad_structure=imrad_data,
            modification_request=request.modification_request,
        )

        # Update paper with new notes using SQLAlchemy
        new_version = persist_generated_reading_notes(paper, notes)
        await db.flush()
        await db.refresh(paper)

        logger.info(
            "Notes regenerated",
            paper_id=request.paper_id,
            version=new_version,
            modification=request.modification_request[:50],
        )

        return GeneratedNotesResponse(
            success=True,
            data=build_generated_notes_payload(
                paper_id=request.paper_id,
                notes=notes,
                version=new_version,
            ),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to regenerate notes", error=str(e), paper_id=request.paper_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to regenerate notes: {str(e)}"),
        )


@router.get("/{paper_id}/export")
async def export_notes(
    paper_id: str, user_id: str = CurrentUserId, db: AsyncSession = Depends(get_db)
):
    """Export reading notes as Markdown."""
    try:
        # Fetch paper data using SQLAlchemy
        result = await db.execute(select(Paper).where(Paper.id == paper_id))
        paper = result.scalar_one_or_none()

        if not paper:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found("Paper not found"),
            )

        if not paper.reading_notes:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found("Notes not yet generated"),
            )

        # Prepare metadata for export
        paper_metadata = {
            "title": paper.title or "Unknown",
            "authors": paper.authors if paper.authors else [],
            "year": str(paper.year) if paper.year else "N/A",
            "venue": paper.venue or "N/A",
            "generated_at": paper.updated_at.isoformat() if paper.updated_at else "N/A",
        }

        # Generate Markdown with header
        markdown = notes_generator.export_to_markdown(
            notes=paper.reading_notes, paper_metadata=paper_metadata
        )

        return {
            "success": True,
            "data": {
                "paperId": paper_id,
                "markdown": markdown,
                "version": paper.notes_version or 0,
                "filename": f"{paper_id}_notes.md",
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to export notes", error=str(e), paper_id=paper_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to export notes: {str(e)}"),
        )


@router.post("/evidence", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
async def save_evidence_note(
    request: EvidenceNoteCreate,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """Save evidence block as a first-class note with source backlink."""
    try:
        evidence_source = get_evidence_source_payload(request.evidence_block.source_chunk_id)
        if not evidence_source:
            evidence_source = await _find_best_evidence_source_payload_db(
                db,
                source_chunk_id=request.evidence_block.source_chunk_id,
                paper_id=request.evidence_block.paper_id,
                section_path=request.evidence_block.section_path,
                page_num=request.evidence_block.page_num,
                text=request.evidence_block.text,
            )
        if not evidence_source:
            evidence_source = find_best_evidence_source_payload(
                source_chunk_id=request.evidence_block.source_chunk_id,
                paper_id=request.evidence_block.paper_id,
                section_path=request.evidence_block.section_path,
                page_num=request.evidence_block.page_num,
                text=request.evidence_block.text,
            )

        canonical_source_chunk_id = str(
            (evidence_source or {}).get("source_chunk_id")
            or request.evidence_block.source_chunk_id
        )
        canonical_paper_id = str(
            (evidence_source or {}).get("paper_id")
            or request.evidence_block.paper_id
        )
        canonical_page_num = (
            (evidence_source or {}).get("page_num")
            if isinstance((evidence_source or {}).get("page_num"), int)
            else request.evidence_block.page_num
        )
        canonical_section_path = str(
            (evidence_source or {}).get("section_path")
            or request.evidence_block.section_path
            or ""
        ) or None
        canonical_content_type = str(
            (evidence_source or {}).get("content_type")
            or request.evidence_block.content_type
            or "text"
        )
        canonical_text = str(
            request.evidence_block.text
            or (evidence_source or {}).get("content")
            or (evidence_source or {}).get("quote_text")
            or (evidence_source or {}).get("anchor_text")
            or ""
        )
        citation_jump_url = str(
            request.evidence_block.citation_jump_url
            or (evidence_source or {}).get("citation_jump_url")
            or build_citation_jump_url(
                paper_id=canonical_paper_id,
                source_chunk_id=canonical_source_chunk_id,
                page_num=canonical_page_num,
                source=request.surface,
            )
        )

        persisted_block = {
            "evidence_id": canonical_source_chunk_id,
            "source_type": request.evidence_block.source_type,
            "paper_id": canonical_paper_id,
            "source_chunk_id": canonical_source_chunk_id,
            "page_num": canonical_page_num,
            "section_path": canonical_section_path,
            "content_type": canonical_content_type,
            "text": canonical_text,
            "score": request.evidence_block.score,
            "rerank_score": request.evidence_block.rerank_score,
            "support_status": request.evidence_block.support_status,
            "citation_jump_url": citation_jump_url,
            "user_comment": request.user_comment,
        }

        if request.target_note_id:
            result = await db.execute(
                select(Note).where(
                    Note.id == request.target_note_id,
                    Note.user_id == user_id,
                )
            )
            note = result.scalar_one_or_none()
            if not note or _is_system_ai_note(note.tags):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=Errors.not_found("Note not found"),
                )
        else:
            note = Note(
                user_id=user_id,
                title=_build_evidence_note_title(request.claim),
                source_type=_normalize_note_source_type(request.surface),
                tags=["evidence", "citation"],
                paper_ids=[canonical_paper_id],
                linked_evidence=[],
            )
            db.add(note)

        existing_evidence = _normalize_linked_evidence(note.linked_evidence)
        note.linked_evidence = [*existing_evidence, persisted_block]
        note.source_type = _normalize_note_source_type(
            note.source_type if request.target_note_id else request.surface
        )

        existing_paper_ids = list(note.paper_ids or [])
        if canonical_paper_id and canonical_paper_id not in existing_paper_ids:
            existing_paper_ids.append(canonical_paper_id)
        note.paper_ids = existing_paper_ids

        if _should_append_evidence_snapshot_to_note(request.target_note_id):
            content_doc = _append_document_content(
                note.content_doc,
                _build_note_body_snapshot(
                    claim=request.claim,
                    evidence_block=persisted_block,
                    user_comment=request.user_comment,
                ),
                note.content,
            )
            _persist_note_content(note, content=None, content_doc=content_doc)

        await db.flush()
        await db.refresh(note)

        logger.info(
            "Evidence note saved",
            note_id=note.id,
            source_chunk_id=request.evidence_block.source_chunk_id,
            user_id=user_id,
            surface=request.surface,
            target_note_id=request.target_note_id,
        )
        return NoteResponse(success=True, data=await _format_note_response_async(note, db))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to save evidence note", error=str(e), user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to save evidence note: {str(e)}"),
        )
