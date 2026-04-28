from __future__ import annotations

import re
from typing import Any

from app.rag_v3.schemas import EvidenceCandidate

_CONTENT_TYPE_VALUES = {"text", "table", "figure", "caption", "page"}
_PAPER_ID_RE = re.compile(r"\b(v2-p-\d{3})\b")


def _safe_content_type(value: Any) -> str:
    if isinstance(value, str) and value in _CONTENT_TYPE_VALUES:
        return value
    return "text"


def extract_paper_ids_from_query(query: str) -> list[str]:
    """Extract any paper IDs (v2-p-XXX) mentioned in the query."""
    return list(dict.fromkeys(_PAPER_ID_RE.findall(query)))


class DenseEvidenceRetriever:
    """Dense retriever backed by Milvus with optional paper-scoped filters."""

    unsupported_field_type_count: int = 0
    fallback_used_count: int = 0

    def __init__(
        self,
        *,
        embedding_provider: Any = None,
        collection_name: str = "",
        milvus_alias: str = "default",
        output_fields: list[str] | None = None,
    ) -> None:
        self._embedding_provider = embedding_provider
        self._collection_name = collection_name
        self._milvus_alias = milvus_alias
        self._output_fields = output_fields or [
            "source_chunk_id",
            "paper_id",
            "normalized_section_path",
            "content_type",
            "anchor_text",
            "page_num",
        ]
        self.last_trace: dict[str, Any] = {}

    @staticmethod
    def _build_filter_expression(
        paper_id_filter: list[str] | None = None,
        section_paths: list[str] | None = None,
        page_from: int | None = None,
        page_to: int | None = None,
        content_types: list[str] | None = None,
    ) -> str:
        parts = ["indexable == true"]

        if paper_id_filter:
            quoted = ", ".join(f'"{paper_id}"' for paper_id in dict.fromkeys(paper_id_filter) if paper_id)
            if quoted:
                parts.append(f"paper_id in [{quoted}]")

        if section_paths:
            normalized = [str(path).strip().lower() for path in section_paths if str(path).strip()]
            if normalized:
                clauses = [f'normalized_section_path like "{path}%"' for path in dict.fromkeys(normalized)]
                parts.append(f"({' || '.join(clauses)})")

        if page_from is not None:
            parts.append(f"page_num >= {int(page_from)}")

        if page_to is not None:
            parts.append(f"page_num <= {int(page_to)}")

        if content_types:
            normalized_types = [
                str(content_type).strip().lower()
                for content_type in content_types
                if str(content_type).strip().lower() in _CONTENT_TYPE_VALUES
            ]
            if normalized_types:
                quoted_types = ", ".join(f'"{content_type}"' for content_type in dict.fromkeys(normalized_types))
                parts.append(f"content_type in [{quoted_types}]")

        return " && ".join(parts)

    def retrieve(
        self,
        query: str,
        top_k: int,
        paper_id_filter: list[str] | None = None,
        section_paths: list[str] | None = None,
        page_from: int | None = None,
        page_to: int | None = None,
        content_types: list[str] | None = None,
    ) -> list[EvidenceCandidate]:
        if not self._embedding_provider or not self._collection_name:
            self.last_trace = {
                "search_path": "disabled",
                "fallback_used": False,
                "error_type": "provider_or_collection_missing",
                "output_fields": [],
            }
            return []

        try:
            result = self._milvus_search(
                query=query,
                top_k=top_k,
                paper_id_filter=paper_id_filter,
                section_paths=section_paths,
                page_from=page_from,
                page_to=page_to,
                content_types=content_types,
                output_fields=self._output_fields,
            )
            self.last_trace = {
                "search_path": "minimal_output_fields",
                "fallback_used": False,
                "error_type": None,
                "output_fields": list(self._output_fields),
            }
            return result
        except Exception as e:
            error_text = str(e)
            unsupported_field = "Unsupported field type" in error_text
            if unsupported_field:
                DenseEvidenceRetriever.unsupported_field_type_count += 1

            DenseEvidenceRetriever.fallback_used_count += 1
            self.last_trace = {
                "search_path": "fallback",
                "fallback_used": True,
                "error_type": "unsupported_field_type" if unsupported_field else "search_error",
                "output_fields": ["source_chunk_id", "paper_id"],
            }

            try:
                return self._milvus_search(
                    query=query,
                    top_k=top_k,
                    paper_id_filter=paper_id_filter,
                    section_paths=section_paths,
                    page_from=page_from,
                    page_to=page_to,
                    content_types=content_types,
                    output_fields=["source_chunk_id", "paper_id"],
                )
            except Exception:
                return []

    def _milvus_search(
        self,
        query: str,
        top_k: int,
        paper_id_filter: list[str] | None = None,
        section_paths: list[str] | None = None,
        page_from: int | None = None,
        page_to: int | None = None,
        content_types: list[str] | None = None,
        output_fields: list[str] | None = None,
    ) -> list[EvidenceCandidate]:
        from pymilvus import Collection

        vec = self._embedding_provider.embed_texts([query])[0]
        col = Collection(self._collection_name, using=self._milvus_alias)
        col.load()

        expr = self._build_filter_expression(
            paper_id_filter=paper_id_filter,
            section_paths=section_paths,
            page_from=page_from,
            page_to=page_to,
            content_types=content_types,
        )

        results = col.search(
            data=[vec],
            anns_field="embedding",
            param={"metric_type": "COSINE", "params": {"nprobe": 10}},
            limit=top_k,
            expr=expr,
            output_fields=output_fields or self._output_fields,
        )
        candidates: list[EvidenceCandidate] = []
        for batch in results:
            for hit in batch:
                e = hit.entity
                source_chunk_id = str(e.get("source_chunk_id") or hit.id or "")
                paper_id = str(e.get("paper_id") or "")
                candidates.append(
                    EvidenceCandidate(
                        source_chunk_id=source_chunk_id,
                        paper_id=paper_id,
                        section_id=str(e.get("normalized_section_path") or e.get("section_path") or ""),
                        content_type=_safe_content_type(e.get("content_type")),
                        anchor_text=str(e.get("anchor_text") or "")[:300],
                        candidate_sources=["dense"],
                        dense_score=float(1 - getattr(hit, "distance", 0.0)),
                    )
                )
        return candidates
