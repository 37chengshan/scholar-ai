"""PDF URL source adapter.

Per D-02: Direct PDF URL validation and download.
Per gpt意见.md Section 4.4: PDF URL adapter rules.

Input formats supported:
- https://example.com/paper.pdf
- https://example.com/paper (with Content-Type: application/pdf)

Constraints:
- Only https:// URLs (http:// rejected for security)
- HEAD request validation for Content-Type and size
- Max file size: 50MB
- Magic bytes validation after download
"""

import os
import re
from typing import Optional

import httpx

from app.services.source_adapters.base_adapter import (
    BaseSourceAdapter,
    SourceResolution,
    MetadataPreview,
)
from app.utils.logger import logger


# Regex for HTTPS URL validation
HTTPS_URL_PATTERN = r"^https://"


class PdfUrlAdapter(BaseSourceAdapter):
    """PDF URL source adapter.

    Validates HTTPS URLs with HEAD request.
    Checks Content-Type and Content-Length headers.
    Downloads and validates PDF magic bytes.
    """

    def __init__(self):
        self.timeout = 30.0
        self.download_timeout = 300.0
        self.max_size_bytes = 50 * 1024 * 1024  # 50MB

    async def resolve(self, input: str) -> SourceResolution:
        """Validate HTTPS URL and check headers.

        Per gpt意见.md Section 4.4:
        - Accept only https:// URLs
        - HEAD request to check Content-Type and Content-Length
        - Return canonical PDF URL
        """
        input = input.strip()

        # Validate HTTPS
        if not re.match(HTTPS_URL_PATTERN, input, re.IGNORECASE):
            return SourceResolution(
                resolved=False,
                source_type="pdf_url",
                error_code="INVALID_URL_PROTOCOL",
                error_message="Only HTTPS URLs are accepted for security",
            )

        # HEAD request for validation
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.head(input, follow_redirects=True)

                # Check Content-Type
                content_type = response.headers.get("content-type", "")
                if "pdf" not in content_type.lower():
                    return SourceResolution(
                        resolved=False,
                        source_type="pdf_url",
                        error_code="INVALID_CONTENT_TYPE",
                        error_message=f"Content-Type is not PDF: {content_type}",
                    )

                # Check Content-Length
                content_length = response.headers.get("content-length")
                if content_length:
                    size = int(content_length)
                    if size > self.max_size_bytes:
                        return SourceResolution(
                            resolved=False,
                            source_type="pdf_url",
                            error_code="FILE_TOO_LARGE",
                            error_message=f"File exceeds 50MB limit: {size} bytes",
                        )

                logger.info(
                    "PDF URL validated",
                    url=input[:100],
                    content_type=content_type,
                    size_bytes=content_length,
                )

                # Use final URL after redirects
                final_url = str(response.url)

                return SourceResolution(
                    resolved=True,
                    source_type="pdf_url",
                    canonical_id=input,  # Original URL as ID
                    canonical_pdf_url=final_url,
                )

        except httpx.HTTPStatusError as e:
            logger.error(
                "PDF URL HEAD request failed",
                url=input[:100],
                status_code=e.response.status_code,
                error=str(e),
            )
            return SourceResolution(
                resolved=False,
                source_type="pdf_url",
                error_code="URL_NOT_ACCESSIBLE",
                error_message=f"URL returned status {e.response.status_code}",
            )
        except Exception as e:
            logger.error(
                "PDF URL validation failed",
                url=input[:100],
                error=str(e),
            )
            return SourceResolution(
                resolved=False,
                source_type="pdf_url",
                error_code="URL_VALIDATION_FAILED",
                error_message=str(e),
            )

    async def fetch_metadata(self, resolution: SourceResolution) -> MetadataPreview:
        """Return minimal metadata for PDF URL.

        Per gpt意见.md Section 4.4:
        - PDF URL has no metadata API
        - Metadata extracted from PDF after download (by processing pipeline)
        - Return pdf_available=True
        """
        if not resolution.resolved:
            return MetadataPreview()

        # PDF URL has no external metadata API
        # Metadata will be extracted during PDF processing
        return MetadataPreview(
            title=None,  # Extracted from PDF
            authors=[],  # Extracted from PDF
            year=None,  # Extracted from PDF
            pdf_available=True,
            pdf_source="direct_url",
        )

    async def acquire_pdf(
        self, resolution: SourceResolution, storage_path: str, storage_key: str
    ) -> str:
        """Download PDF from URL.

        Validates magic bytes after download.
        """
        if not resolution.resolved or not resolution.canonical_pdf_url:
            raise Exception("No PDF URL available")

        pdf_url = resolution.canonical_pdf_url

        # Download PDF
        try:
            async with httpx.AsyncClient(
                timeout=self.download_timeout, follow_redirects=True
            ) as client:
                response = await client.get(pdf_url)
                response.raise_for_status()

                content = response.content

                # Validate magic bytes
                if not content.startswith(b"%PDF-"):
                    raise Exception("Downloaded file is not a valid PDF")

                # Validate size
                if len(content) > self.max_size_bytes:
                    raise Exception(f"Downloaded file exceeds 50MB limit: {len(content)} bytes")

            # Write to storage
            full_path = os.path.join(storage_path, storage_key)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)

            with open(full_path, "wb") as f:
                f.write(content)

            logger.info(
                "PDF URL downloaded",
                url=pdf_url[:100],
                storage_key=storage_key,
                size_bytes=len(content),
            )

            return storage_key

        except httpx.HTTPStatusError as e:
            logger.error(
                "PDF URL download failed",
                url=pdf_url[:100],
                status_code=e.response.status_code,
                error=str(e),
            )
            raise Exception(f"URL returned status {e.response.status_code}")
        except Exception as e:
            logger.error(
                "PDF URL download failed",
                url=pdf_url[:100],
                error=str(e),
            )
            raise


__all__ = ["PdfUrlAdapter"]