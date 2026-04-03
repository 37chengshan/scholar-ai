"""Safety Layer for Agent tool permissions.

Implements D-07 from Agent-Native architecture:
3-level permission control system for Agent tools.

Permission Levels:
- Level 1 (READ): Auto-execute, no confirmation needed
- Level 2 (WRITE): Log audit, auto-execute
- Level 3 (DANGEROUS): Requires user confirmation

Usage:
    safety = SafetyLayer()
    result = await safety.check_permission("delete_paper", context)
    if result["needs_confirmation"]:
        # Ask user for confirmation
        pass
"""

from enum import Enum
from typing import Any, Dict, Optional
from datetime import datetime, timezone

from app.utils.logger import logger


class PermissionLevel(Enum):
    """Permission levels for tool operations.
    
    Levels:
        READ (1): Read-only operations, auto-approved
        WRITE (2): Write operations, logged for audit
        DANGEROUS (3): Dangerous operations, require confirmation
    """
    
    READ = 1
    WRITE = 2
    DANGEROUS = 3


class SafetyLayer:
    """Safety Layer for Agent tool permission control.
    
    Implements 3-level permission system:
    - READ: Auto-approve
    - WRITE: Log audit, auto-approve
    - DANGEROUS: Require user confirmation
    
    Attributes:
        TOOL_PERMISSIONS: Mapping of tool names to permission levels
    """
    
    TOOL_PERMISSIONS: Dict[str, PermissionLevel] = {
        # Level 1: READ operations
        "external_search": PermissionLevel.READ,
        "rag_search": PermissionLevel.READ,
        "list_papers": PermissionLevel.READ,
        "read_paper": PermissionLevel.READ,
        "list_notes": PermissionLevel.READ,
        "read_note": PermissionLevel.READ,
        
        # Level 2: WRITE operations
        "create_note": PermissionLevel.WRITE,
        "update_note": PermissionLevel.WRITE,
        "merge_documents": PermissionLevel.WRITE,
        "extract_references": PermissionLevel.WRITE,
        
        # Level 3: DANGEROUS operations
        "upload_paper": PermissionLevel.DANGEROUS,
        "delete_paper": PermissionLevel.DANGEROUS,
        "execute_command": PermissionLevel.DANGEROUS,
    }
    
    async def check_permission(
        self,
        tool_name: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check if a tool can be executed.
        
        Args:
            tool_name: Name of the tool to check
            context: Execution context (user_id, session_id, etc.)
            
        Returns:
            Dict with:
                - allowed: Whether tool can be executed
                - needs_confirmation: Whether user confirmation is required
                - message: Explanation (for dangerous operations)
        """
        # Get permission level (default to READ for unknown tools)
        level = self.TOOL_PERMISSIONS.get(tool_name, PermissionLevel.READ)
        
        logger.info(
            "Permission check",
            tool=tool_name,
            level=level.name,
            user_id=context.get("user_id")
        )
        
        if level == PermissionLevel.READ:
            # Level 1: Auto-approve
            return {
                "allowed": True,
                "needs_confirmation": False
            }
        
        elif level == PermissionLevel.WRITE:
            # Level 2: Log audit and auto-approve
            await self.log_audit(tool_name, context)
            return {
                "allowed": True,
                "needs_confirmation": False
            }
        
        elif level == PermissionLevel.DANGEROUS:
            # Level 3: Require confirmation
            return {
                "allowed": False,
                "needs_confirmation": True,
                "message": f"Tool '{tool_name}' is a dangerous operation and requires user confirmation."
            }
        
        # Default: treat as READ (safest)
        return {
            "allowed": True,
            "needs_confirmation": False
        }
    
    async def log_audit(
        self,
        tool_name: str,
        context: Dict[str, Any]
    ) -> None:
        """Log audit trail for write operations.
        
        Records tool execution to audit_log table for later review.
        
        Args:
            tool_name: Name of the tool being executed
            context: Execution context (user_id, session_id, parameters, etc.)
        """
        try:
            from app.core.database import get_db_connection
            
            user_id = context.get("user_id")
            session_id = context.get("session_id")
            parameters = context.get("parameters", {})
            
            # Log to database
            async with get_db_connection() as conn:
                await conn.execute(
                    """
                    INSERT INTO audit_log (user_id, session_id, tool_name, parameters, created_at)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    user_id,
                    session_id,
                    tool_name,
                    parameters,
                    datetime.now(timezone.utc)
                )
            
            logger.info(
                "Audit log created",
                tool=tool_name,
                user_id=user_id,
                session_id=session_id
            )
            
        except Exception as e:
            # Log error but don't fail the operation
            logger.error(
                "Failed to create audit log",
                error=str(e),
                tool=tool_name,
                user_id=context.get("user_id")
            )
            # Re-raise in development, suppress in production
            raise