"""Query tool implementations for Agent.

Tools:
- external_search: Search external databases (arXiv, Semantic Scholar)
- rag_search: RAG search over user's library
- list_papers: List papers in user's library
- read_paper: Read paper details
- list_notes: List user's notes
- read_note: Read note content

Each tool returns: {success: bool, data: any, error: str?}
"""

import asyncio
from typing import Any, Dict, List, Optional

from app.api.search import search_arxiv, search_semantic_scholar
from app.core.multimodal_search_service import get_multimodal_search_service
from app.core.database import get_db_connection
from app.utils.logger import logger


async def execute_external_search(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute external_search tool.
    
    Searches arXiv and/or Semantic Scholar for papers.
    
    Args:
        params: {
            "query": str,
            "sources": ["arxiv", "semantic_scholar"],
            "limit": int
        }
    
    Returns:
        {success: bool, data: {results: [...]}, error: str?}
    """
    try:
        query = params.get("query", "")
        sources = params.get("sources", ["arxiv", "semantic_scholar"])
        limit = params.get("limit", 10)
        
        if not query:
            return {"success": False, "error": "Query is required", "data": None}
        
        logger.info("External search initiated", query=query[:50], sources=sources)
        
        # Execute searches in parallel
        tasks = []
        if "arxiv" in sources:
            tasks.append(("arxiv", search_arxiv(query, limit=limit)))
        if "semantic_scholar" in sources:
            tasks.append(("semantic_scholar", search_semantic_scholar(query, limit=limit)))
        
        results_list = await asyncio.gather(
            *[task[1] for task in tasks],
            return_exceptions=True
        )
        
        # Combine results
        all_results = []
        for (source_name, _), result in zip(tasks, results_list):
            if isinstance(result, Exception):
                logger.warning(f"{source_name} search failed", error=str(result))
                continue
            
            source_results = result.get("results", [])
            all_results.extend(source_results)
        
        # TODO: Deduplicate results by arXiv ID + title similarity
        # For now, return all combined results
        
        logger.info(
            "External search completed",
            query=query[:50],
            total_results=len(all_results)
        )
        
        return {
            "success": True,
            "data": {"results": all_results},
            "error": None
        }
        
    except Exception as e:
        logger.error("External search failed", error=str(e), query=params.get("query", "")[:50])
        return {"success": False, "error": str(e), "data": None}


async def execute_rag_search(
    params: Dict[str, Any],
    user_id: str
) -> Dict[str, Any]:
    """Execute rag_search tool.
    
    Queries user's paper library using multimodal RAG.
    
    Args:
        params: {
            "question": str,
            "paper_ids": [str],
            "top_k": int
        }
        user_id: User ID for access control
    
    Returns:
        {success: bool, data: {results: [...], total_count: int}, error: str?}
    """
    try:
        question = params.get("question", "")
        paper_ids = params.get("paper_ids", [])
        top_k = params.get("top_k", 5)
        
        if not question:
            return {"success": False, "error": "Question is required", "data": None}
        
        logger.info(
            "RAG search initiated",
            question=question[:50],
            paper_count=len(paper_ids),
            user_id=user_id
        )
        
        # Get multimodal search service
        service = get_multimodal_search_service()
        
        # Execute search
        result = await service.search(
            query=question,
            paper_ids=paper_ids,
            user_id=user_id,
            top_k=top_k,
            use_reranker=True
        )
        
        logger.info(
            "RAG search completed",
            question=question[:50],
            result_count=len(result.get("results", []))
        )
        
        return {
            "success": True,
            "data": result,
            "error": None
        }
        
    except Exception as e:
        logger.error("RAG search failed", error=str(e), question=params.get("question", "")[:50])
        return {"success": False, "error": str(e), "data": None}


async def execute_list_papers(
    params: Dict[str, Any],
    user_id: str
) -> Dict[str, Any]:
    """Execute list_papers tool.
    
    Lists papers in user's library with optional filters.
    
    Args:
        params: {
            "filter": {status?: str, ...},
            "sort": str,
            "limit": int
        }
        user_id: User ID for ownership
    
    Returns:
        {success: bool, data: {papers: [...]}, error: str?}
    """
    try:
        filter_dict = params.get("filter", {})
        sort = params.get("sort", "created_at")
        limit = params.get("limit", 20)
        
        logger.info("List papers initiated", user_id=user_id, filters=filter_dict)
        
        async with get_db_connection() as conn:
            # Build query
            query = """
                SELECT id, title, authors, year, status, created_at
                FROM papers
                WHERE "userId" = $1
            """
            query_params = [user_id]
            
            # Apply filters
            if "status" in filter_dict:
                query += f' AND status = ${len(query_params) + 1}'
                query_params.append(filter_dict["status"])
            
            # Apply sorting
            valid_sorts = ["created_at", "year", "title"]
            if sort in valid_sorts:
                query += f' ORDER BY "{sort}" DESC'
            
            # Apply limit
            query += f" LIMIT {limit}"
            
            rows = await conn.fetch(query, *query_params)
            
            papers = [dict(row) for row in rows]
        
        logger.info("List papers completed", user_id=user_id, count=len(papers))
        
        return {
            "success": True,
            "data": {"papers": papers},
            "error": None
        }
        
    except Exception as e:
        logger.error("List papers failed", error=str(e), user_id=user_id)
        return {"success": False, "error": str(e), "data": None}


async def execute_read_paper(
    params: Dict[str, Any],
    user_id: str
) -> Dict[str, Any]:
    """Execute read_paper tool.
    
    Retrieves paper details from database.
    
    Args:
        params: {
            "paper_id": str,
            "sections": ["metadata", "abstract", "content", "notes", "chunks"]
        }
        user_id: User ID for access control
    
    Returns:
        {success: bool, data: {paper details}, error: str?}
    """
    try:
        paper_id = params.get("paper_id")
        sections = params.get("sections", ["metadata", "abstract"])
        
        if not paper_id:
            return {"success": False, "error": "Paper ID is required", "data": None}
        
        logger.info("Read paper initiated", paper_id=paper_id, sections=sections)
        
        async with get_db_connection() as conn:
            # Build SELECT clause based on sections
            select_fields = ["id"]
            if "metadata" in sections:
                select_fields.extend(["title", "authors", "year", "doi", "keywords"])
            if "abstract" in sections:
                select_fields.append("abstract")
            if "content" in sections:
                select_fields.append("content")
            if "notes" in sections:
                select_fields.append("reading_notes")
            
            query = f"""
                SELECT {', '.join(select_fields)}
                FROM papers
                WHERE id = $1 AND "userId" = $2
            """
            
            row = await conn.fetchrow(query, paper_id, user_id)
            
            if not row:
                return {
                    "success": False,
                    "error": "Paper not found or access denied",
                    "data": None
                }
            
            paper_data = dict(row)
        
        logger.info("Read paper completed", paper_id=paper_id)
        
        return {
            "success": True,
            "data": paper_data,
            "error": None
        }
        
    except Exception as e:
        logger.error("Read paper failed", error=str(e), paper_id=params.get("paper_id"))
        return {"success": False, "error": str(e), "data": None}


async def execute_list_notes(
    params: Dict[str, Any],
    user_id: str
) -> Dict[str, Any]:
    """Execute list_notes tool.
    
    Lists user's notes with optional filters.
    
    Args:
        params: {
            "filter": {paper_id?: str},
            "limit": int
        }
        user_id: User ID for ownership
    
    Returns:
        {success: bool, data: {notes: [...]}, error: str?}
    """
    try:
        filter_dict = params.get("filter", {})
        limit = params.get("limit", 20)
        
        logger.info("List notes initiated", user_id=user_id)
        
        async with get_db_connection() as conn:
            query = """
                SELECT id, title, content, tags, paper_ids, created_at, updated_at
                FROM notes
                WHERE user_id = $1
            """
            query_params = [user_id]
            
            # Apply filters
            if "paper_id" in filter_dict:
                query += f" AND $${len(query_params) + 1} = ANY(paper_ids)"
                query_params.append(filter_dict["paper_id"])
            
            query += f" ORDER BY created_at DESC LIMIT {limit}"
            
            rows = await conn.fetch(query, *query_params)
            
            notes = [dict(row) for row in rows]
        
        logger.info("List notes completed", user_id=user_id, count=len(notes))
        
        return {
            "success": True,
            "data": {"notes": notes},
            "error": None
        }
        
    except Exception as e:
        logger.error("List notes failed", error=str(e), user_id=user_id)
        return {"success": False, "error": str(e), "data": None}


async def execute_read_note(
    params: Dict[str, Any],
    user_id: str
) -> Dict[str, Any]:
    """Execute read_note tool.
    
    Retrieves note content by ID.
    
    Args:
        params: {"note_id": str}
        user_id: User ID for ownership validation
    
    Returns:
        {success: bool, data: {note details}, error: str?}
    """
    try:
        note_id = params.get("note_id")
        
        if not note_id:
            return {"success": False, "error": "Note ID is required", "data": None}
        
        logger.info("Read note initiated", note_id=note_id)
        
        async with get_db_connection() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, title, content, tags, paper_ids, created_at, updated_at
                FROM notes
                WHERE id = $1 AND user_id = $2
                """,
                note_id,
                user_id
            )
            
            if not row:
                return {
                    "success": False,
                    "error": "Note not found or access denied",
                    "data": None
                }
            
            note_data = dict(row)
        
        logger.info("Read note completed", note_id=note_id)
        
        return {
            "success": True,
            "data": note_data,
            "error": None
        }
        
    except Exception as e:
        logger.error("Read note failed", error=str(e), note_id=params.get("note_id"))
        return {"success": False, "error": str(e), "data": None}