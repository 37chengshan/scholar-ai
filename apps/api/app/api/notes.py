"""Notes API endpoints with Notes 2.0 evidence persistence."""

from typing import Any, List, Literal, Optional
import json

from fastapi import APIRouter, HTTPException, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.orm_note import Note
from app.models.paper import Paper
from app.core.notes_generator import NotesGenerator
from app.services.reading_notes_service import (
    build_generated_notes_payload,
    persist_generated_reading_notes,
)
from app.services.evidence_contract_service import (
    build_citation_jump_url,
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


def _normalize_linked_evidence(value: Optional[list[dict[str, Any]]]) -> list[dict[str, Any]]:
    return [item for item in (value or []) if isinstance(item, dict)]


def _build_note_body_snapshot(
    *,
    claim: str,
    evidence_block: dict[str, Any],
    user_comment: Optional[str] = None,
) -> dict[str, Any]:
    lines = [
        f"Claim: {claim}",
        f"Paper: {evidence_block.get('paper_id') or 'N/A'}",
        f"Page: {evidence_block.get('page_num') or 'N/A'}",
        f"Section: {evidence_block.get('section_path') or 'N/A'}",
        "",
        str(evidence_block.get("text") or ""),
    ]
    if user_comment:
        lines.extend(["", f"Comment: {user_comment}"])

    return _text_to_editor_document("\n".join(lines).strip())


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
        "title": note.title,
        "content": note.content,
        "contentDoc": content_doc,
        "linkedEvidence": _normalize_linked_evidence(note.linked_evidence),
        "sourceType": _normalize_note_source_type(note.source_type),
        "tags": note.tags or [],
        "paperIds": note.paper_ids or [],
        "createdAt": note.created_at.isoformat() if note.created_at else None,
        "updatedAt": note.updated_at.isoformat() if note.updated_at else None,
    }


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

        return NoteResponse(success=True, data=_format_note_response(note))

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
                "notes": [_format_note_response(n) for n in notes],
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

        return NoteResponse(success=True, data=_format_note_response(note))

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

        return NoteResponse(success=True, data=_format_note_response(note))

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
                "notes": [_format_note_response(n) for n in notes],
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
        citation_jump_url = request.evidence_block.citation_jump_url or (
            evidence_source.get("citation_jump_url")
            if evidence_source
            else build_citation_jump_url(
                paper_id=request.evidence_block.paper_id,
                source_chunk_id=request.evidence_block.source_chunk_id,
                page_num=request.evidence_block.page_num,
                source=request.surface,
            )
        )

        persisted_block = {
            "evidence_id": request.evidence_block.evidence_id,
            "source_type": request.evidence_block.source_type,
            "paper_id": request.evidence_block.paper_id,
            "source_chunk_id": request.evidence_block.source_chunk_id,
            "page_num": request.evidence_block.page_num,
            "section_path": request.evidence_block.section_path,
            "content_type": request.evidence_block.content_type,
            "text": request.evidence_block.text,
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
                title=f"Evidence: {request.claim[:80]}",
                source_type=_normalize_note_source_type(request.surface),
                tags=["evidence", "citation"],
                paper_ids=[request.evidence_block.paper_id],
                linked_evidence=[],
            )
            db.add(note)

        existing_evidence = _normalize_linked_evidence(note.linked_evidence)
        note.linked_evidence = [*existing_evidence, persisted_block]
        note.source_type = _normalize_note_source_type(
            note.source_type if request.target_note_id else request.surface
        )

        existing_paper_ids = list(note.paper_ids or [])
        if request.evidence_block.paper_id and request.evidence_block.paper_id not in existing_paper_ids:
            existing_paper_ids.append(request.evidence_block.paper_id)
        note.paper_ids = existing_paper_ids

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
        return NoteResponse(success=True, data=_format_note_response(note))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to save evidence note", error=str(e), user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to save evidence note: {str(e)}"),
        )
