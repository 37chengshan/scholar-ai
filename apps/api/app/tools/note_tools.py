"""Note tool implementations for Agent.

Tools:
- create_note: Create new note (standalone or linked to papers)
- update_note: Update existing note
- ask_user_confirmation: Request user confirmation for dangerous operations

Each tool returns: {success: bool, data: any, error: str?}
"""

from datetime import datetime, timezone
from typing import Any, Dict
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.orm_note import Note
from app.utils.logger import logger


def _serialize_datetime(value: Any) -> str:
    """
    Safely serialize datetime to ISO string.

    Handles both datetime objects and string representations.
    Per D-07: Check type, return string directly if already string.

    Args:
        value: datetime object or string

    Returns:
        ISO formatted string
    """
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _note_to_dict(note: Note) -> Dict[str, Any]:
    """Convert Note ORM object to dictionary for JSON serialization.

    Args:
        note: Note SQLAlchemy model instance

    Returns:
        Dictionary with datetime fields serialized to ISO strings
    """
    return {
        "id": note.id,
        "title": note.title,
        "content": note.content,
        "paper_ids": note.paper_ids or [],
        "tags": note.tags or [],
        "created_at": _serialize_datetime(note.created_at),
        "updated_at": _serialize_datetime(note.updated_at),
    }


async def execute_create_note(
    params: Dict[str, Any],
    **kwargs
) -> Dict[str, Any]:
    """Execute create_note tool.

    Creates a new note in the database.

    Args:
        params: {
            "title": str,
            "content": str,
            "paper_ids": [str],
            "tags": [str]
        }
        **kwargs: Additional context (user_id, session_id)

    Returns:
        {success: bool, data: {note details}, error: str?}
    """
    user_id = kwargs.get("user_id", "")
    try:
        title = params.get("title", "").strip()
        content = params.get("content", "").strip()
        paper_ids = params.get("paper_ids", [])
        tags = params.get("tags", [])

        # Validation
        if not title:
            return {
                "success": False,
                "error": "Title is required",
                "data": None
            }

        if not content:
            return {
                "success": False,
                "error": "Content is required",
                "data": None
            }

        logger.info(
            "Create note initiated",
            user_id=user_id,
            title=title[:50],
            paper_count=len(paper_ids)
        )

        note_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        async with AsyncSessionLocal() as db:
            # Create Note ORM object
            note = Note(
                id=note_id,
                user_id=user_id,
                title=title,
                content=content,
                paper_ids=paper_ids,
                tags=tags,
                created_at=now,
                updated_at=now,
            )

            # Add and commit
            db.add(note)
            await db.commit()
            await db.refresh(note)

            note_data = _note_to_dict(note)

        logger.info("Note created", note_id=note_id, user_id=user_id)

        return {
            "success": True,
            "data": note_data,
            "error": None
        }

    except Exception as e:
        logger.error("Create note failed", error=str(e), user_id=user_id)
        return {"success": False, "error": str(e), "data": None}


async def execute_update_note(
    params: Dict[str, Any],
    **kwargs
) -> Dict[str, Any]:
    """Execute update_note tool.

    Updates an existing note.

    Args:
        params: {
            "note_id": str,
            "updates": {title?: str, content?: str, tags?: [str], paper_ids?: [str]}
        }
        **kwargs: Additional context (user_id, session_id)

    Returns:
        {success: bool, data: {updated note}, error: str?}
    """
    user_id = kwargs.get("user_id", "")
    try:
        note_id = params.get("note_id")
        updates = params.get("updates", {})

        if not note_id:
            return {
                "success": False,
                "error": "Note ID is required",
                "data": None
            }

        if not updates:
            return {
                "success": False,
                "error": "No updates provided",
                "data": None
            }

        logger.info("Update note initiated", note_id=note_id, user_id=user_id)

        async with AsyncSessionLocal() as db:
            # Verify ownership and fetch note
            result = await db.execute(
                select(Note).where(Note.id == note_id, Note.user_id == user_id)
            )
            note = result.scalar_one_or_none()

            if not note:
                return {
                    "success": False,
                    "error": "Note not found or access denied",
                    "data": None
                }

            # Apply updates
            if "title" in updates:
                note.title = updates["title"]
            if "content" in updates:
                note.content = updates["content"]
            if "tags" in updates:
                note.tags = updates["tags"]
            if "paper_ids" in updates:
                note.paper_ids = updates["paper_ids"]

            # Update timestamp (onupdate handler will also update, but we set it explicitly)
            note.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

            # Commit changes
            await db.commit()
            await db.refresh(note)

            note_data = _note_to_dict(note)

        logger.info("Note updated", note_id=note_id, user_id=user_id)

        return {
            "success": True,
            "data": note_data,
            "error": None
        }

    except Exception as e:
        logger.error("Update note failed", error=str(e), note_id=params.get("note_id"))
        return {"success": False, "error": str(e), "data": None}


async def execute_ask_user_confirmation(
    params: Dict[str, Any],
    **kwargs
) -> Dict[str, Any]:
    """Execute ask_user_confirmation tool.

    Returns a confirmation_required signal to the Agent.
    The Agent will pause and wait for user approval.

    Args:
        params: {
            "message": str,
            "details": {operation: str, ...}
        }
        **kwargs: Additional context (ignored)

    Returns:
        {
            success: bool,
            data: {
                confirmation_required: true,
                message: str,
                details: {...}
            },
            error: str?
        }
    """
    try:
        message = params.get("message", "Operation requires confirmation")
        details = params.get("details", {})

        logger.info("User confirmation requested", message=message[:50])

        return {
            "success": True,
            "data": {
                "confirmation_required": True,
                "message": message,
                "details": details
            },
            "error": None
        }

    except Exception as e:
        logger.error("Ask user confirmation failed", error=str(e))
        return {"success": False, "error": str(e), "data": None}