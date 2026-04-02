"""Tests for ImageExtractor service.

Tests cover:
- Image extraction from PDF using pdf2image
- Bounding box handling from Docling
- Caption generation integration
- Embedding generation via BGE-M3
- Error handling and edge cases
"""

import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import numpy as np

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from PIL import Image

from app.core.image_extractor import ImageExtractor, ImageData


class TestImageExtractor:
    """Test ImageExtractor functionality."""

    def test_init(self):
        """Test ImageExtractor initialization."""
        extractor = ImageExtractor()
        assert extractor is not None

    @patch('app.core.image_extractor.convert_from_path')
    def test_extract_images_from_pdf_success(self, mock_convert):
        """Test successful image extraction from PDF."""
        # Create mock images
        mock_img1 = Mock(spec=Image.Image)
        mock_img1.size = (100, 100)
        mock_img2 = Mock(spec=Image.Image)
        mock_img2.size = (200, 150)
        mock_convert.return_value = [mock_img1, mock_img2]

        # Create extractor
        extractor = ImageExtractor()

        # Mock PDF path
        pdf_path = "/fake/path.pdf"

        # Docling items with picture bboxes
        docling_items = [
            {"type": "picture", "page": 1, "bbox": {"l": 0.1, "t": 0.2, "r": 0.5, "b": 0.8}},
            {"type": "text", "page": 1, "text": "Some text"},
        ]

        # Extract images
        images = extractor.extract_images_from_pdf(pdf_path, docling_items)

        # Verify
        assert len(images) == 1  # Only 1 picture item
        assert images[0].page_num == 1
        assert images[0].bbox == {"l": 0.1, "t": 0.2, "r": 0.5, "b": 0.8}
        mock_convert.assert_called_once_with(pdf_path, dpi=150)

    @patch('app.core.image_extractor.convert_from_path')
    def test_extract_images_no_pictures(self, mock_convert):
        """Test extraction when no pictures in PDF."""
        mock_img = Mock(spec=Image.Image)
        mock_convert.return_value = [mock_img]

        extractor = ImageExtractor()
        pdf_path = "/fake/path.pdf"

        # No picture items
        docling_items = [
            {"type": "text", "page": 1, "text": "Some text"},
        ]

        images = extractor.extract_images_from_pdf(pdf_path, docling_items)

        assert len(images) == 0

    @patch('app.core.image_extractor.convert_from_path')
    def test_extract_images_page_out_of_range(self, mock_convert):
        """Test handling of page numbers out of range."""
        mock_img = Mock(spec=Image.Image)
        mock_convert.return_value = [mock_img]  # Only 1 page

        extractor = ImageExtractor()
        pdf_path = "/fake/path.pdf"

        # Picture on page 5, but PDF only has 1 page
        docling_items = [
            {"type": "picture", "page": 5, "bbox": {"l": 0.1, "t": 0.2, "r": 0.5, "b": 0.8}},
        ]

        images = extractor.extract_images_from_pdf(pdf_path, docling_items)

        # Should skip the out-of-range page
        assert len(images) == 0

    @patch('app.core.image_extractor.convert_from_path')
    def test_extract_images_missing_bbox(self, mock_convert):
        """Test handling of pictures without bbox."""
        mock_img = Mock(spec=Image.Image)
        mock_convert.return_value = [mock_img]

        extractor = ImageExtractor()
        pdf_path = "/fake/path.pdf"

        # Picture without bbox
        docling_items = [
            {"type": "picture", "page": 1},  # No bbox
        ]

        images = extractor.extract_images_from_pdf(pdf_path, docling_items)

        # Should still extract with empty bbox
        assert len(images) == 1
        assert images[0].bbox is None

    def test_calculate_pixel_bbox(self):
        """Test bbox conversion from relative to pixel coordinates."""
        extractor = ImageExtractor()

        # Mock image size
        mock_img = Mock(spec=Image.Image)
        mock_img.size = (1000, 2000)

        # Relative bbox
        bbox = {"l": 0.1, "t": 0.2, "r": 0.5, "b": 0.8}

        pixel_bbox = extractor._calculate_pixel_bbox(mock_img, bbox)

        assert pixel_bbox == (100, 400, 500, 1600)  # 0.1*1000, 0.2*2000, etc.

    def test_calculate_pixel_bbox_none(self):
        """Test bbox calculation with None bbox returns None."""
        extractor = ImageExtractor()

        mock_img = Mock(spec=Image.Image)
        mock_img.size = (1000, 2000)

        pixel_bbox = extractor._calculate_pixel_bbox(mock_img, None)

        # Should return None for None bbox
        assert pixel_bbox is None

    @patch('app.core.image_extractor.get_image_caption_service')
    @patch('app.core.image_extractor.get_bge_m3_service')
    async def test_generate_caption_and_embed_success(self, mock_bge, mock_caption):
        """Test successful caption generation and embedding."""
        # Mock caption service
        mock_caption_service = AsyncMock()
        mock_caption_service.generate_caption.return_value = "A sample figure showing data"
        mock_caption.return_value = mock_caption_service

        # Mock BGE service
        mock_bge_service = Mock()
        mock_bge_service.encode_text.return_value = [0.1] * 1024
        mock_bge.return_value = mock_bge_service

        # Create extractor
        extractor = ImageExtractor()

        # Create mock image
        mock_img = Mock(spec=Image.Image)

        # Create ImageData
        image_data = ImageData(
            page_num=1,
            bbox={"l": 0.1, "t": 0.2, "r": 0.5, "b": 0.8},
            image=mock_img
        )

        # Generate caption and embed
        result = await extractor.generate_caption_and_embed(
            image_data,
            paper_id="paper-123",
            user_id="user-456"
        )

        # Verify
        assert result["paper_id"] == "paper-123"
        assert result["user_id"] == "user-456"
        assert result["page_num"] == 1
        assert result["content_type"] == "image"
        assert result["content_data"] == "A sample figure showing data"
        assert result["embedding"] == [0.1] * 1024
        assert result["raw_data"]["bbox"] == {"l": 0.1, "t": 0.2, "r": 0.5, "b": 0.8}

        mock_caption_service.generate_caption.assert_called_once()
        mock_bge_service.encode_text.assert_called_once_with("A sample figure showing data")

    @patch('app.core.image_extractor.get_image_caption_service')
    @patch('app.core.image_extractor.get_bge_m3_service')
    async def test_generate_caption_and_embed_caption_failure(self, mock_bge, mock_caption):
        """Test embedding generation when caption generation fails."""
        # Mock caption service to fail
        mock_caption_service = AsyncMock()
        mock_caption_service.generate_caption.side_effect = Exception("API error")
        mock_caption.return_value = mock_caption_service

        # Mock BGE service
        mock_bge_service = Mock()
        mock_bge_service.encode_text.return_value = [0.1] * 1024
        mock_bge.return_value = mock_bge_service

        extractor = ImageExtractor()
        mock_img = Mock(spec=Image.Image)
        image_data = ImageData(page_num=1, bbox=None, image=mock_img)

        result = await extractor.generate_caption_and_embed(
            image_data,
            paper_id="paper-123",
            user_id="user-456"
        )

        # Should still return result with empty caption
        assert result["content_data"] == ""
        assert result["embedding"] == [0.1] * 1024

    def test_crop_image(self):
        """Test image cropping with bbox."""
        extractor = ImageExtractor()

        # Create a real test image
        img = Image.new('RGB', (1000, 1000), color='red')

        # Crop
        cropped = extractor._crop_image(img, (100, 100, 400, 400))

        assert cropped.size == (300, 300)

    def test_crop_image_none_bbox(self):
        """Test image cropping with None bbox returns original."""
        extractor = ImageExtractor()

        img = Image.new('RGB', (1000, 1000), color='red')

        # Crop with None bbox
        cropped = extractor._crop_image(img, None)

        assert cropped == img


class TestImageData:
    """Test ImageData dataclass."""

    def test_image_data_creation(self):
        """Test ImageData creation."""
        mock_img = Mock(spec=Image.Image)

        data = ImageData(
            page_num=2,
            bbox={"l": 0.0, "t": 0.0, "r": 1.0, "b": 1.0},
            image=mock_img
        )

        assert data.page_num == 2
        assert data.bbox == {"l": 0.0, "t": 0.0, "r": 1.0, "b": 1.0}
        assert data.image == mock_img


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
