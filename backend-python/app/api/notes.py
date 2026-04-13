"""Notes API endpoints.

Provides CRUD endpoints for user notes:
- GET /api/v1/notes - List notes with filters
- POST /api/v1/notes - Create note
- GET /api/v1/notes/:id - Get note
- PUT /api/v1/notes/:id - Update note
- DELETE /api/v1/notes/:id - Delete note
- GET /api/v1/notes/paper/:paperId - Get notes for paper
- POST /api/v1/notes/generate - Generate reading notes (AI)
- POST /api/v1/notes/regenerate - Regenerate with modification
"""

from typing import List, Optional
import json

from fastapi import APIRouter, HTTPException, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func, desc, asc, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.orm_note import Note
from app.models.paper import Paper
from app.core.notes_generator import NotesGenerator
from app.utils.logger import logger
from app.deps import CurrentUserId
from app.utils.problem_detail import Errors

router = APIRouter()
notes_generator = NotesGenerator()


# =============================================================================
# Request/Response Models
# =============================================================================


class NoteCreate(BaseModel):
    """Request to create a note."""

    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    tags: List[str] = Field(default=[])
    paperIds: List[str] = Field(default=[], alias="paperIds")

    class Config:
        populate_by_name = True


class NoteUpdate(BaseModel):
    """Request to update a note."""

    title: Optional[str] = Field(None, min_length=1, max_length=500)
    content: Optional[str] = Field(None, min_length=1)
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
    return {
        "id": note.id,
        "userId": note.user_id,
        "title": note.title,
        "content": note.content,
        "tags": note.tags or [],
        "paperIds": note.paper_ids or [],
        "createdAt": note.created_at.isoformat() if note.created_at else None,
        "updatedAt": note.updated_at.isoformat() if note.updated_at else None,
    }


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
            content=request.content,
            tags=request.tags,
            paper_ids=request.paperIds,
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
    sortBy: str = Query("created_at", description="Sort field"),
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
        # Build query
        query = select(Note).where(Note.user_id == user_id)

        # Filter by paperId (notes where paper_ids contains the paperId)
        if paperId:
            query = query.where(Note.paper_ids.contains([paperId]))

        # Filter by tag
        if tag:
            query = query.where(Note.tags.contains([tag]))

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply sorting
        order_func = desc if order == "desc" else asc
        sort_column = getattr(Note, sortBy, Note.created_at)
        query = query.order_by(order_func(sort_column))

        # Apply pagination
        query = query.offset(offset).limit(limit)

        result = await db.execute(query)
        notes = result.scalars().all()

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

        if not note:
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

        if not note:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found("Note not found"),
            )

        # Update fields
        if request.title is not None:
            note.title = request.title
        if request.content is not None:
            note.content = request.content
        if request.tags is not None:
            note.tags = request.tags
        if request.paperIds is not None:
            note.paper_ids = request.paperIds

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

        if not note:
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
        query = (
            select(Note)
            .where(Note.user_id == user_id, Note.paper_ids.contains([paper_id]))
            .order_by(desc(Note.created_at))
        )

        result = await db.execute(query)
        notes = result.scalars().all()

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
        new_version = (paper.notes_version or 0) + 1
        paper.reading_notes = notes
        paper.notes_version = new_version
        await db.flush()
        await db.refresh(paper)

        logger.info("Notes generated", paper_id=request.paper_id, version=new_version)

        return GeneratedNotesResponse(
            paper_id=request.paper_id, notes=notes, version=new_version
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
        new_version = (paper.notes_version or 0) + 1
        paper.reading_notes = notes
        paper.notes_version = new_version
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
            data={
                "paperId": request.paper_id,
                "notes": notes,
                "version": new_version,
            },
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
