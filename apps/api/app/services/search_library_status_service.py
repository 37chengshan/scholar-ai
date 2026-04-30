from __future__ import annotations

from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.paper import Paper
from app.utils.logger import logger


class SearchLibraryStatusService:
    """Annotate external search results with canonical library status."""

    async def annotate_results(
        self,
        results: list[dict[str, Any]],
        *,
        user: Any,
        db: AsyncSession,
    ) -> list[dict[str, Any]]:
        if user is None or not results:
            return results

        try:
            for result in results:
                result["libraryStatus"] = "not_imported"
                result["in_library"] = False

            arxiv_ids = [r.get("arxivId") for r in results if r.get("arxivId")]
            s2_ids = [r.get("s2PaperId") for r in results if r.get("s2PaperId")]
            dois = [r.get("doi") for r in results if r.get("doi")]

            conditions = []
            if arxiv_ids:
                conditions.append(Paper.arxiv_id.in_(arxiv_ids))
            if s2_ids:
                conditions.append(Paper.s2_paper_id.in_(s2_ids))
            if dois:
                conditions.append(Paper.doi.in_(dois))

            if not conditions:
                return results

            stmt = select(
                Paper.arxiv_id,
                Paper.s2_paper_id,
                Paper.doi,
                Paper.is_search_ready,
            ).where(
                Paper.user_id == user.id,
                or_(*conditions),
            )
            rows = (await db.execute(stmt)).all()

            paper_map: dict[tuple[str, str], bool] = {}
            for arxiv_id, s2_paper_id, doi, is_search_ready in rows:
                if arxiv_id:
                    paper_map[("arxiv", arxiv_id)] = bool(is_search_ready)
                if s2_paper_id:
                    paper_map[("s2", s2_paper_id)] = bool(is_search_ready)
                if doi:
                    paper_map[("doi", doi)] = bool(is_search_ready)

            for result in results:
                matched = None
                if result.get("arxivId"):
                    matched = paper_map.get(("arxiv", result["arxivId"]))
                if matched is None and result.get("s2PaperId"):
                    matched = paper_map.get(("s2", result["s2PaperId"]))
                if matched is None and result.get("doi"):
                    matched = paper_map.get(("doi", result["doi"]))
                if matched is None:
                    continue

                result["in_library"] = True
                result["libraryStatus"] = (
                    "imported_fulltext_ready"
                    if matched
                    else "imported_metadata_only"
                )
        except Exception as exc:
            logger.warning("library_status annotation failed", error=str(exc))

        return results


search_library_status_service = SearchLibraryStatusService()
