"""Notes API endpoints

Provides endpoints for generating, regenerating, and exporting reading notes.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from app.core.notes_generator import NotesGenerator
from app.core.database import postgres_db
from app.utils.logger import logger

router = APIRouter()
notes_generator = NotesGenerator()


class GenerateNotesRequest(BaseModel):
    """Request to generate notes for a paper."""
    paper_id: str


class RegenerateNotesRequest(BaseModel):
    """Request to regenerate notes with modification."""
    paper_id: str
    modification_request: str


class NotesResponse(BaseModel):
    """Response with generated notes."""
    paper_id: str
    notes: str
    version: int


@router.post("/generate", response_model=NotesResponse)
async def generate_notes(request: GenerateNotesRequest):
    """
    Generate reading notes for a paper.

    Args:
        request: GenerateNotesRequest with paper_id

    Returns:
        Generated notes with version info
    """
    import json

    try:
        # Fetch paper data
        row = await postgres_db.fetchrow(
            """SELECT title, authors, year, venue, imrad_json, notes_version
               FROM papers WHERE id = $1""",
            request.paper_id
        )

        if not row:
            raise HTTPException(status_code=404, detail="Paper not found")

        imrad_data = row["imrad_json"]
        if not imrad_data:
            raise HTTPException(status_code=400, detail="Paper not yet parsed")

        # Parse imrad_json if it's a string
        if isinstance(imrad_data, str):
            imrad_data = json.loads(imrad_data)

        # Prepare metadata
        paper_metadata = {
            "title": row["title"] or "Unknown",
            "authors": row["authors"] if row["authors"] else [],
            "year": row["year"] or "",
            "venue": row["venue"] or ""
        }

        # Generate notes
        notes = await notes_generator.generate_notes(
            paper_metadata=paper_metadata,
            imrad_structure=imrad_data
        )

        # Update paper with new notes
        new_version = (row["notes_version"] or 0) + 1
        await postgres_db.execute(
            """UPDATE papers
               SET reading_notes = $1,
                   notes_version = $2,
                   updated_at = NOW()
               WHERE id = $3""",
            notes,
            new_version,
            request.paper_id
        )

        logger.info(
            "Notes generated",
            paper_id=request.paper_id,
            version=new_version
        )

        return NotesResponse(
            paper_id=request.paper_id,
            notes=notes,
            version=new_version
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate notes: {e}", paper_id=request.paper_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/regenerate", response_model=NotesResponse)
async def regenerate_notes(request: RegenerateNotesRequest):
    """
    Regenerate reading notes with modification request.

    Args:
        request: RegenerateNotesRequest with paper_id and modification_request

    Returns:
        Regenerated notes with version info
    """
    import json

    try:
        # Fetch paper data
        row = await postgres_db.fetchrow(
            """SELECT title, authors, year, venue, imrad_json, notes_version
               FROM papers WHERE id = $1""",
            request.paper_id
        )

        if not row:
            raise HTTPException(status_code=404, detail="Paper not found")

        imrad_data = row["imrad_json"]
        if not imrad_data:
            raise HTTPException(status_code=400, detail="Paper not yet parsed")

        # Parse imrad_json if it's a string
        if isinstance(imrad_data, str):
            imrad_data = json.loads(imrad_data)

        # Prepare metadata
        paper_metadata = {
            "title": row["title"] or "Unknown",
            "authors": row["authors"] if row["authors"] else [],
            "year": row["year"] or "",
            "venue": row["venue"] or ""
        }

        # Regenerate notes with modification request
        notes = await notes_generator.regenerate_notes(
            paper_metadata=paper_metadata,
            imrad_structure=imrad_data,
            modification_request=request.modification_request
        )

        # Update paper with new notes
        new_version = (row["notes_version"] or 0) + 1
        await postgres_db.execute(
            """UPDATE papers
               SET reading_notes = $1,
                   notes_version = $2,
                   updated_at = NOW()
               WHERE id = $3""",
            notes,
            new_version,
            request.paper_id
        )

        logger.info(
            "Notes regenerated",
            paper_id=request.paper_id,
            version=new_version,
            modification=request.modification_request[:50]
        )

        return NotesResponse(
            paper_id=request.paper_id,
            notes=notes,
            version=new_version
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to regenerate notes: {e}", paper_id=request.paper_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{paper_id}")
async def get_notes(paper_id: str):
    """
    Get reading notes for a paper.

    Args:
        paper_id: The paper ID

    Returns:
        Notes data if available
    """
    try:
        row = await postgres_db.fetchrow(
            """SELECT reading_notes, notes_version, status
               FROM papers WHERE id = $1""",
            paper_id
        )

        if not row:
            raise HTTPException(status_code=404, detail="Paper not found")

        return {
            "paper_id": paper_id,
            "notes": row["reading_notes"],
            "version": row["notes_version"] or 0,
            "has_notes": row["reading_notes"] is not None,
            "status": row["status"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get notes: {e}", paper_id=paper_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{paper_id}/export")
async def export_notes(paper_id: str):
    """
    Export reading notes as Markdown.

    Args:
        paper_id: The paper ID

    Returns:
        Markdown formatted notes with metadata header
    """
    import json

    try:
        row = await postgres_db.fetchrow(
            """SELECT title, authors, year, venue, reading_notes, notes_version, updated_at
               FROM papers WHERE id = $1""",
            paper_id
        )

        if not row:
            raise HTTPException(status_code=404, detail="Paper not found")

        if not row["reading_notes"]:
            raise HTTPException(status_code=404, detail="Notes not yet generated")

        # Prepare metadata for export
        paper_metadata = {
            "title": row["title"] or "Unknown",
            "authors": row["authors"] if row["authors"] else [],
            "year": row["year"] or "N/A",
            "venue": row["venue"] or "N/A",
            "generated_at": row["updated_at"].isoformat() if row["updated_at"] else "N/A"
        }

        # Generate Markdown with header
        markdown = notes_generator.export_to_markdown(
            notes=row["reading_notes"],
            paper_metadata=paper_metadata
        )

        return {
            "paper_id": paper_id,
            "markdown": markdown,
            "version": row["notes_version"] or 0,
            "filename": f"{paper_id}_notes.md"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export notes: {e}", paper_id=paper_id)
        raise HTTPException(status_code=500, detail=str(e))
