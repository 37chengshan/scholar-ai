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
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select, and_, any_

from app.api.search import search_arxiv, search_semantic_scholar
from app.core.multimodal_search_service import get_multimodal_search_service
from app.database import AsyncSessionLocal
from app.models.paper import Paper
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


async def execute_external_search(params: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """Execute external_search tool.

    Searches arXiv and/or Semantic Scholar for papers.

    Args:
        params: {
            "query": str,
            "sources": ["arxiv", "semantic_scholar"],
            "limit": int
        }
        **kwargs: Additional context (ignored for external search)

    Returns:
        {success: bool, data: {results: [...]}, error: str?}
    """
    try:
        query = params.get("query", "")
        sources = params.get("sources", ["semantic_scholar"])
        limit = params.get("limit", 10)

        if not query:
            return {"success": False, "error": "Query is required", "data": None}

        logger.info("External search initiated", query=query[:50], sources=sources)

        # Execute searches in parallel (default: Semantic Scholar only for better quality)
        tasks = []
        if "semantic_scholar" in sources:
            tasks.append(
                (
                    "semantic_scholar",
                    search_semantic_scholar(query, limit=limit, offset=0),
                )
            )
        if "arxiv" in sources:
            tasks.append(("arxiv", search_arxiv(query, limit=limit, offset=0)))

        results_list = await asyncio.gather(
            *[task[1] for task in tasks], return_exceptions=True
        )

        # Combine results
        all_results = []
        for (source_name, _), result in zip(tasks, results_list):
            if isinstance(result, Exception):
                logger.warning(f"{source_name} search failed", error=str(result))
                continue

            source_results = result.get("results", [])
            # Convert SearchResult objects to dicts for JSON serialization
            # Optimize: Only include essential fields to reduce token usage
            for item in source_results:
                if hasattr(item, "model_dump"):
                    full_data = item.model_dump()
                    # Keep only essential fields
                    optimized = {
                        "id": full_data.get("id"),
                        "title": full_data.get("title"),
                        "authors": full_data.get("authors", [])[:3],  # Max 3 authors
                        "year": full_data.get("year"),
                        "abstract": full_data.get("abstract", "")[:200] + "..."
                        if len(full_data.get("abstract", "")) > 200
                        else full_data.get("abstract"),
                        "source": full_data.get("source"),
                        "citationCount": full_data.get("citationCount"),
                    }
                    all_results.append(optimized)
                else:
                    all_results.append(item)

        # TODO: Deduplicate results by arXiv ID + title similarity
        # For now, return all combined results

        logger.info(
            "External search completed",
            query=query[:50],
            total_results=len(all_results),
        )

        return {"success": True, "data": {"results": all_results}, "error": None}

    except Exception as e:
        logger.error(
            "External search failed", error=str(e), query=params.get("query", "")[:50]
        )
        return {"success": False, "error": str(e), "data": None}


async def execute_rag_search(params: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """Execute rag_search tool.

    Queries user's paper library using multimodal RAG.

    Args:
        params: {
            "question": str,
            "paper_ids": [str],
            "top_k": int
        }
        **kwargs: Additional context (user_id, session_id)

    Returns:
        {success: bool, data: {results: [...], total_count: int}, error: str?}
    """
    user_id = kwargs.get("user_id", "")
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
            user_id=user_id,
        )

        # Get multimodal search service
        service = get_multimodal_search_service()

        # Execute search
        result = await service.search(
            query=question,
            paper_ids=paper_ids,
            user_id=user_id,
            top_k=top_k,
            use_reranker=True,
        )

        logger.info(
            "RAG search completed",
            question=question[:50],
            result_count=len(result.get("results", [])),
        )

        return {"success": True, "data": result, "error": None}

    except Exception as e:
        logger.error(
            "RAG search failed", error=str(e), question=params.get("question", "")[:50]
        )
        return {"success": False, "error": str(e), "data": None}


async def execute_list_papers(params: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """Execute list_papers tool.

    Lists papers in user's library with optional filters.

    Args:
        params: {
            "filter": {status?: str, ...},
            "sort": str,
            "limit": int
        }
        **kwargs: Additional context (user_id, session_id)

    Returns:
        {success: bool, data: {papers: [...]}, error: str?}
    """
    user_id = kwargs.get("user_id", "")
    try:
        filter_dict = params.get("filter", {})
        sort = params.get("sort", "created_at")
        limit = params.get("limit", 20)

        logger.info("List papers initiated", user_id=user_id, filters=filter_dict)

        async with AsyncSessionLocal() as db:
            # Build query with SQLAlchemy ORM
            # Select specific fields to optimize response
            stmt = select(Paper).where(Paper.user_id == user_id)

            # Apply filters
            if "status" in filter_dict:
                stmt = stmt.where(Paper.status == filter_dict["status"])

            # Apply sorting
            sort_column_map = {
                "created_at": Paper.created_at,
                "year": Paper.year,
                "title": Paper.title,
            }
            sort_column = sort_column_map.get(sort, Paper.created_at)
            stmt = stmt.order_by(sort_column.desc())

            # Apply limit
            stmt = stmt.limit(limit)

            result = await db.execute(stmt)
            papers = result.scalars().all()

            # Convert to dict format for JSON serialization
            papers_data = []
            for paper in papers:
                paper_dict = {
                    "id": paper.id,
                    "title": paper.title,
                    "authors": paper.authors,
                    "year": paper.year,
                    "status": paper.status,
                    "createdAt": _serialize_datetime(paper.created_at),
                }
                papers_data.append(paper_dict)

        logger.info("List papers completed", user_id=user_id, count=len(papers_data))

        return {"success": True, "data": {"papers": papers_data}, "error": None}

    except Exception as e:
        logger.error("List papers failed", error=str(e), user_id=user_id)
        return {"success": False, "error": str(e), "data": None}


async def execute_read_paper(params: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """Execute read_paper tool.

    Retrieves paper details from database.

    Args:
        params: {
            "paper_id": str,
            "sections": ["metadata", "abstract", "content", "notes", "chunks"]
        }
        **kwargs: Additional context (user_id, session_id)

    Returns:
        {success: bool, data: {paper: {...}}, error: str?}
    """
    user_id = kwargs.get("user_id", "")
    try:
        paper_id = params.get("paper_id")
        sections = params.get("sections", ["metadata", "abstract"])

        if not paper_id:
            return {"success": False, "error": "Paper ID is required", "data": None}

        logger.info("Read paper initiated", paper_id=paper_id, sections=sections)

        async with AsyncSessionLocal() as db:
            # Build query with SQLAlchemy ORM
            stmt = select(Paper).where(
                and_(Paper.id == paper_id, Paper.user_id == user_id)
            )

            result = await db.execute(stmt)
            paper = result.scalar_one_or_none()

            if not paper:
                return {
                    "success": False,
                    "error": "Paper not found or access denied",
                    "data": None,
                }

            # Build response based on requested sections
            paper_data = {"id": paper.id}
            if "metadata" in sections:
                paper_data.update({
                    "title": paper.title,
                    "authors": paper.authors,
                    "year": paper.year,
                    "doi": paper.doi,
                    "keywords": paper.keywords,
                })
            if "abstract" in sections:
                paper_data["abstract"] = paper.abstract
            if "content" in sections:
                paper_data["content"] = paper.content
            if "notes" in sections:
                paper_data["reading_notes"] = paper.reading_notes

        logger.info("Read paper completed", paper_id=paper_id)

        return {"success": True, "data": paper_data, "error": None}

    except Exception as e:
        logger.error("Read paper failed", error=str(e), paper_id=params.get("paper_id"))
        return {"success": False, "error": str(e), "data": None}


async def execute_list_notes(params: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """Execute list_notes tool.

    Lists user's notes with optional filters.

    Args:
        params: {
            "filter": {paper_id?: str},
            "limit": int
        }
        **kwargs: Additional context (user_id, session_id)

    Returns:
        {success: bool, data: {notes: [...]}, error: str?}
    """
    user_id = kwargs.get("user_id", "")
    try:
        filter_dict = params.get("filter", {})
        limit = params.get("limit", 20)

        logger.info("List notes initiated", user_id=user_id)

        async with AsyncSessionLocal() as db:
            # Build query with SQLAlchemy ORM
            stmt = select(Note).where(Note.user_id == user_id)

            # Apply filters - check if paper_id is in paper_ids array
            if "paper_id" in filter_dict:
                stmt = stmt.where(filter_dict["paper_id"] == any_(Note.paper_ids))

            stmt = stmt.order_by(Note.created_at.desc()).limit(limit)

            result = await db.execute(stmt)
            notes = result.scalars().all()

            # Convert to dict format for JSON serialization
            notes_data = []
            for note in notes:
                note_dict = {
                    "id": note.id,
                    "title": note.title,
                    "content": note.content,
                    "tags": note.tags,
                    "paper_ids": note.paper_ids,
                    "created_at": _serialize_datetime(note.created_at),
                    "updated_at": _serialize_datetime(note.updated_at),
                }
                notes_data.append(note_dict)

        logger.info("List notes completed", user_id=user_id, count=len(notes_data))

        return {"success": True, "data": {"notes": notes_data}, "error": None}

    except Exception as e:
        logger.error("List notes failed", error=str(e), user_id=user_id)
        return {"success": False, "error": str(e), "data": None}


async def execute_read_note(params: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """Execute read_note tool.

    Retrieves note content by ID.

    Args:
        params: {"note_id": str}
        **kwargs: Additional context (user_id, session_id)

    Returns:
        {success: bool, data: {note details}, error: str?}
    """
    user_id = kwargs.get("user_id", "")
    try:
        note_id = params.get("note_id")

        if not note_id:
            return {"success": False, "error": "Note ID is required", "data": None}

        logger.info("Read note initiated", note_id=note_id)

        async with AsyncSessionLocal() as db:
            # Build query with SQLAlchemy ORM
            stmt = select(Note).where(
                and_(Note.id == note_id, Note.user_id == user_id)
            )

            result = await db.execute(stmt)
            note = result.scalar_one_or_none()

            if not note:
                return {
                    "success": False,
                    "error": "Note not found or access denied",
                    "data": None,
                }

            # Convert to dict format for JSON serialization
            note_data = {
                "id": note.id,
                "title": note.title,
                "content": note.content,
                "tags": note.tags,
                "paper_ids": note.paper_ids,
                "created_at": _serialize_datetime(note.created_at),
                "updated_at": _serialize_datetime(note.updated_at),
            }

        logger.info("Read note completed", note_id=note_id)

        return {"success": True, "data": note_data, "error": None}

    except Exception as e:
        logger.error("Read note failed", error=str(e), note_id=params.get("note_id"))
        return {"success": False, "error": str(e), "data": None}
