"""Advanced tool implementations for Agent.

Tools:
- extract_references: Extract citations from papers
- merge_documents: Merge multiple documents
- execute_command: Execute system command (requires confirmation)
- show_message: Display message to user

Each tool returns: {success: bool, data: any, error: str?}
"""

import re
from typing import Any, Dict, List

from app.utils.logger import logger


async def execute_extract_references(params: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """
    Extract reference list from papers.

    Args:
        params: {
            "paper_ids": [str],
            "format": "apa" | "mla" | "chicago" | "bibtex"
        }
        **kwargs: user_id, session_id

    Returns:
        {success: bool, data: {references: [...], format: str}, error: str?}
    """
    import re
    from app.core.database import get_db_connection
    
    user_id = kwargs.get("user_id", "")
    
    try:
        paper_ids = params.get("paper_ids", [])
        format_style = params.get("format", "apa")
        
        if not paper_ids:
            return {"success": False, "error": "paper_ids is required", "data": None}
        
        logger.info("Extracting references", paper_count=len(paper_ids), format=format_style)
        
        all_references = []
        
        async with get_db_connection() as conn:
            for paper_id in paper_ids:
                # Verify user owns the paper
                paper = await conn.fetchrow(
                    "SELECT title, content FROM papers WHERE id = $1 AND user_id = $2",
                    paper_id, user_id
                )
                
                if not paper:
                    continue
                
                # Extract references section from content
                content = paper.get("content", "") or ""
                references = _parse_references_section(content, format_style)
                all_references.extend(references)
        
        # Deduplicate references
        unique_refs = _deduplicate_references(all_references)
        
        # Format according to style
        formatted_refs = _format_references(unique_refs, format_style)
        
        return {
            "success": True,
            "data": {
                "references": formatted_refs,
                "format": format_style,
                "total_count": len(formatted_refs)
            },
            "error": None
        }
        
    except Exception as e:
        logger.error("extract_references failed", error=str(e))
        return {"success": False, "error": str(e), "data": None}


def _parse_references_section(content: str, format_style: str) -> list:
    """Parse references section from paper content."""
    # Find references section
    ref_pattern = r'(?:References|REFERENCES|Bibliography)\s*\n([\s\S]*?)(?:\n\s*\n|$)'
    match = re.search(ref_pattern, content)
    
    if not match:
        return []
    
    ref_text = match.group(1)
    
    # Parse individual references (simplified - could use Docling for better parsing)
    refs = []
    # Match numbered or bulleted references
    ref_items = re.split(r'\n(?=\[\d+\]|\d+\.|•)', ref_text)
    
    for item in ref_items:
        item = item.strip()
        if item:
            refs.append({"raw": item, "parsed": _parse_citation(item)})
    
    return refs


def _parse_citation(text: str) -> Dict:
    """Parse a single citation into structured data."""
    # Simplified parsing - could use LLM for better extraction
    authors = ""
    title = ""
    year = ""
    
    # Try to extract year
    year_match = re.search(r'\((\d{4})\)', text)
    if year_match:
        year = year_match.group(1)
    
    # Try to extract title (usually in quotes or before period)
    title_match = re.search(r'"([^"]+)"|([^.]+)\.', text)
    if title_match:
        title = title_match.group(1) or title_match.group(2)
    
    return {"authors": authors, "title": title, "year": year, "raw": text}


def _format_references(refs: list, style: str) -> list:
    """Format references according to citation style."""
    formatted = []
    
    for ref in refs:
        parsed = ref.get("parsed", {})
        raw = ref.get("raw", "")
        
        if style == "apa":
            # APA: Author, A. A. (Year). Title. Journal.
            formatted.append(raw)  # Simplified - use raw for now
        elif style == "bibtex":
            formatted.append(f"@article{{,\n  author = {{{parsed.get('authors', '')}}},\n  title = {{{parsed.get('title', '')}}},\n  year = {{{parsed.get('year', '')}}}\n}}")
        else:
            formatted.append(raw)
    
    return formatted


def _deduplicate_references(refs: list) -> list:
    """Remove duplicate references."""
    seen = set()
    unique = []
    
    for ref in refs:
        # Use parsed title as dedup key
        key = ref.get("parsed", {}).get("title", "").lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(ref)
    
    return unique


async def execute_merge_documents(params: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """Execute merge_documents tool.

    Merges content from multiple sources.

    Args:
        params: {"sources": [...], "output_format": str, "title": str?}
        **kwargs: Additional context (ignored)

    Returns:
        {success: bool, data: {merged_content: str}, error: str?}
    """
    try:
        sources = params.get("sources", [])

        logger.info("Merge documents initiated", source_count=len(sources))

        # Placeholder - actual implementation would combine content

        return {
            "success": True,
            "data": {"merged_content": "", "message": "Document merge pending implementation"},
            "error": None
        }

    except Exception as e:
        logger.error("Merge documents failed", error=str(e))
        return {"success": False, "error": str(e), "data": None}


async def execute_execute_command(params: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """
    Execute a tool chain (multiple tools in sequence).

    Args:
        params: {
            "command": str,  # e.g., "extract_references → create_note"
            "args": dict     # Arguments for the chain
        }
        **kwargs: user_id, session_id, tool_registry

    Returns:
        {success: bool, data: {results: [...], final_output: any}, error: str?}
    """
    user_id = kwargs.get("user_id", "")
    tool_registry = kwargs.get("tool_registry")
    
    try:
        command = params.get("command", "")
        args = params.get("args", {})
        
        if not command:
            return {"success": False, "error": "command is required", "data": None}
        
        # Parse tool chain
        # Format: "tool1 → tool2 → tool3"
        tool_names = [t.strip() for t in command.split("→")]
        
        logger.info("Executing tool chain", tools=tool_names, user_id=user_id)
        
        results = []
        current_data = args
        
        for i, tool_name in enumerate(tool_names):
            if not tool_registry:
                return {"success": False, "error": "Tool registry not available", "data": None}
            
            tool = tool_registry.get(tool_name)
            if not tool:
                return {
                    "success": False,
                    "error": f"Tool '{tool_name}' not found in chain",
                    "data": {"results": results, "failed_at_step": i + 1}
                }
            
            # Check if dangerous tool - need confirmation
            if tool.needs_confirmation:
                return {
                    "success": False,
                    "needs_confirmation": True,
                    "message": f"Tool '{tool_name}' requires confirmation",
                    "tool_name": tool_name,
                    "data": {"results": results, "pending_step": i + 1}
                }
            
            # Execute tool
            result = await tool_registry.execute(tool_name, current_data, **kwargs)
            
            results.append({
                "step": i + 1,
                "tool": tool_name,
                "success": result.get("success", False),
                "output": result.get("data")
            })
            
            if not result.get("success"):
                return {
                    "success": False,
                    "error": f"Tool '{tool_name}' failed: {result.get('error')}",
                    "data": {"results": results, "failed_at_step": i + 1}
                }
            
            # Pass output to next tool
            current_data = result.get("data", {})
        
        logger.info("Tool chain completed", tools=tool_names, steps=len(results))
        
        return {
            "success": True,
            "data": {
                "results": results,
                "final_output": current_data,
                "steps_completed": len(results)
            },
            "error": None
        }
        
    except Exception as e:
        logger.error("execute_command failed", error=str(e))
        return {"success": False, "error": str(e), "data": None}


async def execute_show_message(params: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """Execute show_message tool.

    Displays a message to the user.

    Args:
        params: {"message": str, "type": str}
        **kwargs: Additional context (ignored)

    Returns:
        {success: bool, data: {displayed: bool}, error: str?}
    """
    try:
        message = params.get("message", "")
        msg_type = params.get("type", "info")

        logger.info("Show message", message=message[:50], type=msg_type)

        return {
            "success": True,
            "data": {"displayed": True, "message": message, "type": msg_type},
            "error": None
        }

    except Exception as e:
        logger.error("Show message failed", error=str(e))
        return {"success": False, "error": str(e), "data": None}