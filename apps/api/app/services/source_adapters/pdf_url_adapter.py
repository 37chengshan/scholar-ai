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

    def _is_pdf_like_content_type(self, content_type: str) -> bool:
        lowered = (content_type or "").lower()
        return "pdf" in lowered or "application/octet-stream" in lowered

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

        # HEAD request for validation (fallback to GET probe when HEAD is not reliable)
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.head(input, follow_redirects=True)

                if response.status_code >= 400:
                    raise httpx.HTTPStatusError(
                        f"HEAD returned status {response.status_code}",
                        request=response.request,
                        response=response,
                    )

                # Check Content-Type
                content_type = response.headers.get("content-type", "")
                if not self._is_pdf_like_content_type(content_type):
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
            logger.warning(
                "PDF URL HEAD failed, fallback to GET probe",
                url=input[:100],
                status_code=e.response.status_code,
                error=str(e),
            )
            return await self._resolve_with_get_probe(input)
        except Exception as e:
            logger.warning(
                "PDF URL HEAD validation failed, fallback to GET probe",
                url=input[:100],
                error=str(e),
            )
            return await self._resolve_with_get_probe(input)

    async def _resolve_with_get_probe(self, input_url: str) -> SourceResolution:
        """Fallback probe when HEAD is not supported or unreliable."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                async with client.stream("GET", input_url, headers={"Range": "bytes=0-2047"}) as response:
                    response.raise_for_status()

                    content_type = response.headers.get("content-type", "")

                    sampled = bytearray()
                    async for chunk in response.aiter_bytes():
                        sampled.extend(chunk)
                        if len(sampled) >= 2048:
                            break
                    content = bytes(sampled)

                    if not self._is_pdf_like_content_type(content_type) and not content.startswith(b"%PDF-"):
                        return SourceResolution(
                            resolved=False,
                            source_type="pdf_url",
                            error_code="INVALID_CONTENT_TYPE",
                            error_message=f"GET probe is not PDF: {content_type}",
                        )

                    content_length = response.headers.get("content-length")
                    if content_length and int(content_length) > self.max_size_bytes:
                        return SourceResolution(
                            resolved=False,
                            source_type="pdf_url",
                            error_code="FILE_TOO_LARGE",
                            error_message=f"File exceeds 50MB limit: {content_length} bytes",
                        )

                    return SourceResolution(
                        resolved=True,
                        source_type="pdf_url",
                        canonical_id=input_url,
                        canonical_pdf_url=str(response.url),
                    )
        except httpx.HTTPStatusError as e:
            logger.error(
                "PDF URL GET probe failed",
                url=input_url[:100],
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
                "PDF URL GET probe validation failed",
                url=input_url[:100],
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
                async with client.stream("GET", pdf_url) as response:
                    response.raise_for_status()

                    content_type = response.headers.get("content-type", "")
                    if not self._is_pdf_like_content_type(content_type):
                        raise Exception(f"Content-Type is not PDF: {content_type}")

                    content_length = response.headers.get("content-length")
                    if content_length and int(content_length) > self.max_size_bytes:
                        raise Exception(f"Downloaded file exceeds 50MB limit: {content_length} bytes")

                    chunks = []
                    total_size = 0
                    async for chunk in response.aiter_bytes():
                        total_size += len(chunk)
                        if total_size > self.max_size_bytes:
                            raise Exception(f"Downloaded file exceeds 50MB limit: {total_size} bytes")
                        chunks.append(chunk)

                content = b"".join(chunks)

                # Validate magic bytes
                if not content.startswith(b"%PDF-"):
                    raise Exception("Downloaded file is not a valid PDF")

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