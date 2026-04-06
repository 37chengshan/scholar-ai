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

from app.core.database import get_db_connection
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
        
        async with get_db_connection() as conn:
            # Insert note
            await conn.execute(
                """
                INSERT INTO notes (id, user_id, title, content, paper_ids, tags, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                note_id,
                user_id,
                title,
                content,
                paper_ids,
                tags,
                now,
                now
            )
            
            # Fetch created note
            row = await conn.fetchrow(
                """
                SELECT id, title, content, paper_ids, tags, created_at, updated_at
                FROM notes
                WHERE id = $1
                """,
                note_id
            )
            
            note_data = dict(row) if row else None
            
            # Convert datetime to ISO string for JSON serialization
            if note_data and "created_at" in note_data:
                note_data["created_at"] = _serialize_datetime(note_data["created_at"])
            if note_data and "updated_at" in note_data:
                note_data["updated_at"] = _serialize_datetime(note_data["updated_at"])
        
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
        
        async with get_db_connection() as conn:
            # Verify ownership
            existing = await conn.fetchrow(
                "SELECT id FROM notes WHERE id = $1 AND user_id = $2",
                note_id,
                user_id
            )
            
            if not existing:
                return {
                    "success": False,
                    "error": "Note not found or access denied",
                    "data": None
                }
            
            # Build update query
            update_fields = []
            update_values = []
            param_idx = 1
            
            if "title" in updates:
                update_fields.append(f"title = ${param_idx}")
                update_values.append(updates["title"])
                param_idx += 1
            
            if "content" in updates:
                update_fields.append(f"content = ${param_idx}")
                update_values.append(updates["content"])
                param_idx += 1
            
            if "tags" in updates:
                update_fields.append(f"tags = ${param_idx}")
                update_values.append(updates["tags"])
                param_idx += 1
            
            if "paper_ids" in updates:
                update_fields.append(f"paper_ids = ${param_idx}")
                update_values.append(updates["paper_ids"])
                param_idx += 1
            
            # Always update timestamp
            update_fields.append(f"updated_at = ${param_idx}")
            update_values.append(datetime.now(timezone.utc))
            param_idx += 1
            
            # Add WHERE clause parameters
            update_values.extend([note_id, user_id])
            
            query = f"""
                UPDATE notes
                SET {', '.join(update_fields)}
                WHERE id = ${param_idx} AND user_id = ${param_idx + 1}
            """
            
            await conn.execute(query, *update_values)
            
            # Fetch updated note
            row = await conn.fetchrow(
                """
                SELECT id, title, content, paper_ids, tags, created_at, updated_at
                FROM notes
                WHERE id = $1
                """,
                note_id
            )
            
            note_data = dict(row) if row else None
            
            # Convert datetime to ISO string for JSON serialization
            if note_data and "created_at" in note_data:
                note_data["created_at"] = _serialize_datetime(note_data["created_at"])
            if note_data and "updated_at" in note_data:
                note_data["updated_at"] = _serialize_datetime(note_data["updated_at"])
        
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