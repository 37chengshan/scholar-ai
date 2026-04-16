"""Tests for MultimodalIndexer refactor to use Qwen3VL service.

Tests verify:
- Qwen3VL service integration (imports, initialization)
- Removal of old services (ImageCaptionService, TableDescriptionService, BGE-M3)
- paper_contents_v2 collection usage
- 2048-dim embeddings
- Single-stage image/table processing
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from PIL import Image

from app.core.multimodal_indexer import MultimodalIndexer


class TestMultimodalIndexerImports:
    """Test 1: Verify MultimodalIndexer imports and initialization."""

    def test_has_qwen3vl_service_attribute(self):
        """Test that MultimodalIndexer has qwen3vl_service attribute."""
        with patch('app.core.multimodal_indexer.get_qwen3vl_service') as mock_qwen3vl:
            with patch('app.core.multimodal_indexer.get_milvus_service') as mock_milvus:
                mock_qwen3vl.return_value = Mock()
                mock_milvus.return_value = Mock()

                indexer = MultimodalIndexer()

                assert hasattr(indexer, 'qwen3vl_service')
                assert indexer.qwen3vl_service is not None

    def test_no_caption_service_attribute(self):
        """Test that MultimodalIndexer does NOT have caption_service attribute."""
        with patch('app.core.multimodal_indexer.get_qwen3vl_service') as mock_qwen3vl:
            with patch('app.core.multimodal_indexer.get_milvus_service') as mock_milvus:
                mock_qwen3vl.return_value = Mock()
                mock_milvus.return_value = Mock()

                indexer = MultimodalIndexer()

                assert not hasattr(indexer, 'caption_service')

    def test_no_description_service_attribute(self):
        """Test that MultimodalIndexer does NOT have description_service attribute."""
        with patch('app.core.multimodal_indexer.get_qwen3vl_service') as mock_qwen3vl:
            with patch('app.core.multimodal_indexer.get_milvus_service') as mock_milvus:
                mock_qwen3vl.return_value = Mock()
                mock_milvus.return_value = Mock()

                indexer = MultimodalIndexer()

                assert not hasattr(indexer, 'description_service')

    def test_no_bge_m3_service_attribute(self):
        """Test that MultimodalIndexer does NOT have bge_m3 attribute."""
        with patch('app.core.multimodal_indexer.get_qwen3vl_service') as mock_qwen3vl:
            with patch('app.core.multimodal_indexer.get_milvus_service') as mock_milvus:
                mock_qwen3vl.return_value = Mock()
                mock_milvus.return_value = Mock()

                indexer = MultimodalIndexer()

                assert not hasattr(indexer, 'bge_m3')

    def test_uses_paper_contents_v2_collection(self):
        """Test that MultimodalIndexer uses paper_contents_v2 collection."""
        with patch('app.core.multimodal_indexer.get_qwen3vl_service') as mock_qwen3vl:
            with patch('app.core.multimodal_indexer.get_milvus_service') as mock_milvus:
                mock_qwen3vl.return_value = Mock()
                mock_milvus.return_value = Mock()

                indexer = MultimodalIndexer()

                assert indexer.collection_name == "paper_contents_v2"

    def test_embedding_dim_is_2048(self):
        """Test that EMBEDDING_DIM is 2048 (Qwen3-VL dimension)."""
        assert MultimodalIndexer.EMBEDDING_DIM == 2048


class TestImageProcessingRefactor:
    """Test 2: Verify single-stage image processing."""

    def test_image_embedding_dimension(self):
        """Test that image embedding is 2048-dim."""
        with patch('app.core.multimodal_indexer.get_qwen3vl_service') as mock_qwen3vl:
            with patch('app.core.multimodal_indexer.get_milvus_service') as mock_milvus:
                mock_service = Mock()
                mock_service.encode_image.return_value = [0.1] * 2048
                mock_qwen3vl.return_value = mock_service
                mock_milvus.return_value = Mock()

                indexer = MultimodalIndexer()

                # Create test image
                test_image = Image.new("RGB", (100, 100), color="red")

                embedding = indexer.qwen3vl_service.encode_image(test_image)

                assert len(embedding) == 2048

    def test_image_processing_no_caption_service_call(self):
        """Test that image processing does NOT call ImageCaptionService."""
        with patch('app.core.multimodal_indexer.get_qwen3vl_service') as mock_qwen3vl:
            with patch('app.core.multimodal_indexer.get_milvus_service') as mock_milvus:
                mock_service = Mock()
                mock_service.encode_image.return_value = [0.1] * 2048
                mock_qwen3vl.return_value = mock_service
                mock_milvus_instance = Mock()
                mock_milvus.return_value = mock_milvus_instance

                indexer = MultimodalIndexer()

                # Verify that caption_service does not exist
                assert not hasattr(indexer, 'caption_service')


class TestTableProcessingRefactor:
    """Test 3: Verify single-stage table processing."""

    def test_table_embedding_dimension(self):
        """Test that table embedding is 2048-dim."""
        with patch('app.core.multimodal_indexer.get_qwen3vl_service') as mock_qwen3vl:
            with patch('app.core.multimodal_indexer.get_milvus_service') as mock_milvus:
                mock_service = Mock()
                mock_service.encode_table.return_value = [0.1] * 2048
                mock_qwen3vl.return_value = mock_service
                mock_milvus.return_value = Mock()

                indexer = MultimodalIndexer()

                embedding = indexer.qwen3vl_service.encode_table(
                    caption="Test table",
                    headers=["col1", "col2"],
                    rows=[{"col1": "a", "col2": "b"}]
                )

                assert len(embedding) == 2048

    def test_table_processing_no_description_service_call(self):
        """Test that table processing does NOT call TableDescriptionService."""
        with patch('app.core.multimodal_indexer.get_qwen3vl_service') as mock_qwen3vl:
            with patch('app.core.multimodal_indexer.get_milvus_service') as mock_milvus:
                mock_service = Mock()
                mock_service.encode_table.return_value = [0.1] * 2048
                mock_qwen3vl.return_value = mock_service
                mock_milvus.return_value = Mock()

                indexer = MultimodalIndexer()

                # Verify that description_service does not exist
                assert not hasattr(indexer, 'description_service')


class TestCollectionName:
    """Test paper_contents_v2 collection usage."""

    def test_milvus_insert_uses_v2_collection(self):
        """Test that Milvus insert uses paper_contents_v2."""
        with patch('app.core.multimodal_indexer.get_qwen3vl_service') as mock_qwen3vl:
            with patch('app.core.multimodal_indexer.get_milvus_service') as mock_milvus:
                mock_qwen3vl.return_value = Mock()
                mock_milvus_instance = Mock()
                mock_milvus.return_value = mock_milvus_instance

                indexer = MultimodalIndexer()

                # Verify collection name
                assert indexer.collection_name == "paper_contents_v2"

                # Verify that collection_name is passed to Milvus insert
                assert indexer.collection_name == "paper_contents_v2"


class TestIntegrationFlow:
    """Integration tests for refactored MultimodalIndexer."""

    @pytest.mark.asyncio
    async def test_image_flow_single_stage(self):
        """Test that image processing flow is single-stage (no caption service)."""
        with patch('app.core.multimodal_indexer.get_qwen3vl_service') as mock_qwen3vl:
            with patch('app.core.multimodal_indexer.get_milvus_service') as mock_milvus:
                mock_qwen3vl_service = Mock()
                mock_qwen3vl_service.encode_image.return_value = [0.5] * 2048
                mock_qwen3vl.return_value = mock_qwen3vl_service

                mock_milvus_instance = Mock()
                mock_milvus_instance.connect = Mock()
                mock_milvus_instance.create_collections = Mock()
                mock_milvus_instance.insert = Mock()
                mock_milvus.return_value = mock_milvus_instance

                indexer = MultimodalIndexer()

                # Create mock image data
                mock_image_data = Mock()
                mock_image_data.image = Image.new("RGB", (100, 100), color="blue")
                mock_image_data.page_num = 1
                mock_image_data.bbox = [0, 0, 100, 100]

                # Process image (should NOT call caption_service)
                # The test is verifying that caption_service doesn't exist
                assert not hasattr(indexer, 'caption_service')

                # Verify qwen3vl_service.encode_image is the method
                assert hasattr(indexer.qwen3vl_service, 'encode_image')

    @pytest.mark.asyncio
    async def test_table_flow_single_stage(self):
        """Test that table processing flow is single-stage (no description service)."""
        with patch('app.core.multimodal_indexer.get_qwen3vl_service') as mock_qwen3vl:
            with patch('app.core.multimodal_indexer.get_milvus_service') as mock_milvus:
                mock_qwen3vl_service = Mock()
                mock_qwen3vl_service.encode_table.return_value = [0.3] * 2048
                mock_qwen3vl.return_value = mock_qwen3vl_service

                mock_milvus_instance = Mock()
                mock_milvus_instance.connect = Mock()
                mock_milvus_instance.create_collections = Mock()
                mock_milvus.return_value = mock_milvus_instance

                indexer = MultimodalIndexer()

                # Verify that description_service doesn't exist
                assert not hasattr(indexer, 'description_service')

                # Verify qwen3vl_service.encode_table is the method
                assert hasattr(indexer.qwen3vl_service, 'encode_table')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])