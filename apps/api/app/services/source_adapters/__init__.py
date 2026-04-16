"""Source adapters for external paper sources.

Per D-02: Five source adapters (local_file/arxiv/pdf_url/doi/semantic_scholar).
Per D-07: Strict throttling with import domain rate limiter.

Adapters:
- ArxivAdapter: arXiv ID/URL resolution and PDF download
- S2Adapter: Semantic Scholar paper resolution with openAccessPdf
- DoiAdapter: DOI resolution via CrossRef + S2 PDF check
- PdfUrlAdapter: Direct PDF URL validation and download
"""

from app.services.source_adapters.base_adapter import (
    BaseSourceAdapter,
    SourceResolution,
    MetadataPreview,
)
from app.services.source_adapters.arxiv_adapter import ArxivAdapter
from app.services.source_adapters.s2_adapter import S2Adapter
from app.services.source_adapters.doi_adapter import DoiAdapter
from app.services.source_adapters.pdf_url_adapter import PdfUrlAdapter

__all__ = [
    "BaseSourceAdapter",
    "SourceResolution",
    "MetadataPreview",
    "ArxivAdapter",
    "S2Adapter",
    "DoiAdapter",
    "PdfUrlAdapter",
]