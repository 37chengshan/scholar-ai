"""Tool implementations for Agent.

This module provides execution implementations for all 15+ tools defined in the Tool Registry.

Tool Categories:
- Query Tools (6): external_search, rag_search, list_papers, read_paper, list_notes, read_note
- Note Tools (3): create_note, update_note, ask_user_confirmation
- Paper Tools (2): upload_paper, delete_paper
- Advanced Tools (4): extract_references, merge_documents, execute_command, show_message

Usage:
    from app.tools import register_all_tools
    from app.core.tool_registry import ToolRegistry

    registry = ToolRegistry()
    register_all_tools(registry)
"""

from app.core.tool_registry import ToolRegistry
from app.tools.query_tools import (
    execute_external_search,
    execute_rag_search,
    execute_list_papers,
    execute_read_paper,
    execute_list_notes,
    execute_read_note,
)
from app.tools.note_tools import (
    execute_create_note,
    execute_update_note,
    execute_ask_user_confirmation,
)
from app.tools.paper_tools import (
    execute_upload_paper,
    execute_delete_paper,
)
from app.tools.advanced_tools import (
    execute_extract_references,
    execute_merge_documents,
    execute_execute_command,
    execute_show_message,
)


def register_all_tools(registry: ToolRegistry) -> None:
    """Register all tool executors with the Tool Registry.

    This function maps tool names to their execution functions.
    The Tool Registry will call these functions when execute() is called.

    Args:
        registry: ToolRegistry instance to register executors with

    Example:
        >>> registry = ToolRegistry()
        >>> register_all_tools(registry)
        >>> result = await registry.execute("external_search", {"query": "transformers"})
    """
    # Query Tools
    registry.register_executor("external_search", execute_external_search)
    registry.register_executor("rag_search", execute_rag_search)
    registry.register_executor("list_papers", execute_list_papers)
    registry.register_executor("read_paper", execute_read_paper)
    registry.register_executor("list_notes", execute_list_notes)
    registry.register_executor("read_note", execute_read_note)

    # Note Tools
    registry.register_executor("create_note", execute_create_note)
    registry.register_executor("update_note", execute_update_note)
    registry.register_executor("ask_user_confirmation", execute_ask_user_confirmation)

    # Paper Tools
    registry.register_executor("upload_paper", execute_upload_paper)
    registry.register_executor("delete_paper", execute_delete_paper)

    # Advanced Tools
    registry.register_executor("extract_references", execute_extract_references)
    registry.register_executor("merge_documents", execute_merge_documents)
    registry.register_executor("execute_command", execute_execute_command)
    registry.register_executor("show_message", execute_show_message)


__all__ = [
    "register_all_tools",
    "execute_external_search",
    "execute_rag_search",
    "execute_list_papers",
    "execute_read_paper",
    "execute_list_notes",
    "execute_read_note",
    "execute_create_note",
    "execute_update_note",
    "execute_ask_user_confirmation",
    "execute_upload_paper",
    "execute_delete_paper",
    "execute_extract_references",
    "execute_merge_documents",
    "execute_execute_command",
    "execute_show_message",
]