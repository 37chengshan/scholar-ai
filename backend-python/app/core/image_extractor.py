"""Image extraction service for PDF documents.

Provides:
- Image extraction from PDF pages using Docling bounding boxes
- Integration with pdf2image for PDF to PIL Image conversion
- 2048-dim embedding generation via Qwen3VL service (multimodal)
- Structured data output for Milvus storage
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from PIL import Image

from app.core.qwen3vl_service import get_qwen3vl_service
from app.utils.logger import logger


try:
    from pdf2image import convert_from_path
except ImportError:
    convert_from_path = None
    logger.warning("pdf2image not installed, image extraction will be disabled")


@dataclass
class ImageData:
    """Container for extracted image data."""
    page_num: int
    bbox: Optional[Dict[str, float]]
    image: Image.Image


class ImageExtractor:
    """Extract images from PDF documents and generate embeddings."""

    DEFAULT_DPI = 150
    EMBEDDING_DIM = 2048  # Qwen3VL outputs 2048-dim

    def __init__(self):
        """Initialize the image extractor."""
        self._qwen3vl_service = None

    def _get_qwen3vl_service(self):
        """Lazy load Qwen3VL service."""
        if self._qwen3vl_service is None:
            self._qwen3vl_service = get_qwen3vl_service()
        return self._qwen3vl_service

    def extract_images_from_pdf(
        self,
        pdf_path: str,
        docling_items: List[Dict[str, Any]]
    ) -> List[ImageData]:
        """Extract images from PDF using Docling bounding boxes.

        Args:
            pdf_path: Path to the PDF file
            docling_items: List of items from Docling parser containing picture types

        Returns:
            List of ImageData objects containing extracted images
        """
        if convert_from_path is None:
            logger.warning("pdf2image not available, skipping image extraction")
            return []

        # Filter for picture items
        picture_items = [
            item for item in docling_items
            if item.get("type") == "picture"
        ]

        if not picture_items:
            logger.debug("No picture items found in document")
            return []

        try:
            # Convert PDF pages to images
            logger.info(
                "Converting PDF to images",
                pdf_path=pdf_path,
                picture_count=len(picture_items)
            )
            pages = convert_from_path(pdf_path, dpi=self.DEFAULT_DPI)
        except Exception as e:
            logger.error("Failed to convert PDF to images", error=str(e))
            return []

        extracted_images = []

        for item in picture_items:
            page_num = item.get("page", 1)
            bbox = item.get("bbox")

            # Validate page number (1-indexed)
            if page_num < 1 or page_num > len(pages):
                logger.warning(
                    "Page number out of range",
                    page_num=page_num,
                    total_pages=len(pages)
                )
                continue

            # Get page image
            page_image = pages[page_num - 1]  # Convert to 0-indexed

            # Calculate pixel bbox
            pixel_bbox = self._calculate_pixel_bbox(page_image, bbox)

            # Crop image
            cropped_image = self._crop_image(page_image, pixel_bbox)

            extracted_images.append(ImageData(
                page_num=page_num,
                bbox=bbox,
                image=cropped_image
            ))

            logger.debug(
                "Extracted image",
                page_num=page_num,
                bbox=bbox,
                cropped_size=cropped_image.size
            )

        logger.info(
            "Image extraction complete",
            extracted_count=len(extracted_images)
        )
        return extracted_images

    def _calculate_pixel_bbox(
        self,
        image: Image.Image,
        bbox: Optional[Dict[str, float]]
    ) -> Optional[Tuple[int, int, int, int]]:
        """Convert relative bbox to pixel coordinates.

        Args:
            image: PIL Image
            bbox: Relative bbox with keys l, t, r, b (0-1 range)

        Returns:
            Tuple of (left, top, right, bottom) in pixels, or None for full image
        """
        if bbox is None:
            return None

        width, height = image.size

        left = int(bbox.get("l", 0) * width)
        top = int(bbox.get("t", 0) * height)
        right = int(bbox.get("r", 1) * width)
        bottom = int(bbox.get("b", 1) * height)

        # Ensure valid coordinates
        left = max(0, left)
        top = max(0, top)
        right = min(width, right)
        bottom = min(height, bottom)

        return (left, top, right, bottom)

    def _crop_image(
        self,
        image: Image.Image,
        bbox: Optional[Tuple[int, int, int, int]]
    ) -> Image.Image:
        """Crop image to bounding box.

        Args:
            image: PIL Image to crop
            bbox: Tuple of (left, top, right, bottom) in pixels

        Returns:
            Cropped image or original if bbox is None
        """
        if bbox is None:
            return image

        return image.crop(bbox)

    async def generate_caption_and_embed(
        self,
        image_data: ImageData,
        paper_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Generate embedding for an image using Qwen3VL multimodal encoding.

        Args:
            image_data: ImageData object containing the extracted image
            paper_id: UUID of the paper
            user_id: UUID of the user

        Returns:
            Dictionary ready for Milvus insertion with:
            - paper_id, user_id, page_num, content_type
            - content_data: placeholder (direct image encoding, no caption needed)
            - raw_data: bbox info
            - embedding: 2048-dim vector
        """
        qwen3vl_service = self._get_qwen3vl_service()

        # Direct image encoding via Qwen3VL (no caption generation needed)
        try:
            embedding = await qwen3vl_service.encode_image(image_data.image)
            logger.debug("Generated image embedding", dim=len(embedding))
            # Note: content_data is empty since we directly encode the image
            caption = ""  # Placeholder - actual image content is in embedding
        except Exception as e:
            logger.error("Failed to encode image", error=str(e))
            embedding = [0.0] * self.EMBEDDING_DIM
            caption = ""

        return {
            "paper_id": paper_id,
            "user_id": user_id,
            "page_num": image_data.page_num,
            "content_type": "image",
            "content_data": caption,  # Empty placeholder
            "raw_data": {
                "bbox": image_data.bbox,
            },
            "embedding": embedding,
        }

    async def process_pdf_images(
        self,
        pdf_path: str,
        docling_items: List[Dict[str, Any]],
        paper_id: str,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """Process all images from a PDF.

        Convenience method that extracts and embeds all images.

        Args:
            pdf_path: Path to PDF file
            docling_items: Docling parsed items
            paper_id: Paper UUID
            user_id: User UUID

        Returns:
            List of dictionaries ready for Milvus insertion
        """
        images = self.extract_images_from_pdf(pdf_path, docling_items)

        results = []
        for image_data in images:
            try:
                result = await self.generate_caption_and_embed(
                    image_data, paper_id, user_id
                )
                results.append(result)
            except Exception as e:
                logger.error(
                    "Failed to process image",
                    page_num=image_data.page_num,
                    error=str(e)
                )
                # Continue processing other images

        return results
