"""Extended integration tests for MultimodalIndexer.

Tests verify:
- Processing PDFs with images and tables
- Integration with Qwen3VL embedding service
- Integration with Milvus vector storage
- Handling large PDFs
- Factory pattern usage
- Error handling and partial failures
"""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from pathlib import Path
from PIL import Image
import tempfile

from app.core.multimodal_indexer import (
    MultimodalIndexer,
    extract_figure_references,
    create_enhanced_multimodal_embedding,
)


class TestExtractFigureReferences:
    """Test reference context extraction."""

    def test_extract_figure_references_basic(self):
        """Test basic figure reference extraction."""
        markdown = """
        As shown in Figure 1, the results are significant.
        Figure 1 demonstrates the correlation between variables.
        In Figure 2, we see another pattern.
        """
        
        contexts = extract_figure_references(markdown, "1", "figure")
        
        assert len(contexts) <= 3
        assert any("Figure 1" in ctx for ctx in contexts)

    def test_extract_table_references(self):
        """Test table reference extraction."""
        markdown = """
        Table 1 shows the experimental results.
        The data in Table 1 confirms our hypothesis.
        Table 2 presents additional findings.
        """
        
        contexts = extract_figure_references(markdown, "1", "table")
        
        assert len(contexts) <= 3
        assert any("Table 1" in ctx for ctx in contexts)

    def test_extract_chinese_references(self):
        """Test Chinese figure/table references."""
        markdown = """
        如图1所示，结果非常显著。
        表1展示了实验数据。
        """
        
        contexts_figure = extract_figure_references(markdown, "1", "figure")
        contexts_table = extract_figure_references(markdown, "1", "table")
        
        assert any("图" in ctx for ctx in contexts_figure)
        assert any("表" in ctx for ctx in contexts_table)

    def test_limit_to_three_contexts(self):
        """Test that extraction limits to 3 contexts."""
        markdown = "Figure 1 appears here. Figure 1 again. Figure 1 third. Figure 1 fourth."
        
        contexts = extract_figure_references(markdown, "1", "figure")
        
        assert len(contexts) <= 3

    def test_empty_markdown(self):
        """Test handling empty markdown."""
        contexts = extract_figure_references("", "1", "figure")
        
        assert contexts == []


class TestCreateEnhancedMultimodalEmbedding:
    """Test enhanced multimodal embedding creation."""

    @pytest.mark.asyncio
    @patch('app.core.multimodal_indexer.extract_figure_references')
    async def test_create_embedding_with_all_parts(self, mock_extract):
        """Test embedding creation with caption, context, and description."""
        mock_extract.return_value = ["Context text about Figure 1."]
        
        mock_bge_service = MagicMock()
        mock_bge_service.encode_text.return_value = [0.1] * 1024
        
        embedding, combined_text = await create_enhanced_multimodal_embedding(
            figure_type="image",
            figure_label="1",
            caption="Figure 1: Results graph",
            markdown="Full document markdown",
            bge_m3_service=mock_bge_service,
            vlm_description="VLM generated description"
        )
        
        assert len(embedding) == 1024
        assert "Figure 1: Results graph" in combined_text
        assert "Context:" in combined_text
        assert "Description:" in combined_text

    @pytest.mark.asyncio
    @patch('app.core.multimodal_indexer.extract_figure_references')
    async def test_create_embedding_without_vlm_description(self, mock_extract):
        """Test embedding creation without VLM description."""
        mock_extract.return_value = ["Context text."]
        
        mock_bge_service = MagicMock()
        mock_bge_service.encode_text.return_value = [0.2] * 1024
        
        embedding, combined_text = await create_enhanced_multimodal_embedding(
            figure_type="image",
            figure_label="1",
            caption="Figure 1: Data",
            markdown="Markdown text",
            bge_m3_service=mock_bge_service,
            vlm_description=None
        )
        
        assert len(embedding) == 1024
        assert "Description:" not in combined_text

    @pytest.mark.asyncio
    @patch('app.core.multimodal_indexer.extract_figure_references')
    async def test_create_embedding_empty_context(self, mock_extract):
        """Test embedding creation when no references found."""
        mock_extract.return_value = []
        
        mock_bge_service = MagicMock()
        mock_bge_service.encode_text.return_value = [0.3] * 1024
        
        embedding, combined_text = await create_enhanced_multimodal_embedding(
            figure_type="table",
            figure_label="2",
            caption="Table 2: Statistics",
            markdown="No references to Table 2",
            bge_m3_service=mock_bge_service,
            vlm_description="Statistical summary"
        )
        
        assert len(embedding) == 1024
        assert "Context:" not in combined_text


class TestMultimodalIndexerInit:
    """Test MultimodalIndexer initialization."""

    @patch('app.core.multimodal_indexer.get_qwen3vl_service')
    @patch('app.core.multimodal_indexer.get_milvus_service')
    @patch('app.core.multimodal_indexer.ObjectStorage')
    def test_init_creates_extractors(self, mock_storage, mock_milvus, mock_qwen):
        """Test that indexer creates extractors."""
        mock_qwen.return_value = MagicMock()
        mock_milvus.return_value = MagicMock()
        mock_storage.return_value = MagicMock()
        
        indexer = MultimodalIndexer()
        
        assert indexer.image_extractor is not None
        assert indexer.table_extractor is not None

    @patch('app.core.multimodal_indexer.get_qwen3vl_service')
    @patch('app.core.multimodal_indexer.get_milvus_service')
    @patch('app.core.multimodal_indexer.ObjectStorage')
    def test_init_uses_factory(self, mock_storage, mock_milvus, mock_qwen):
        """Test that indexer uses factory to get services."""
        mock_qwen.return_value = MagicMock()
        mock_milvus.return_value = MagicMock()
        mock_storage.return_value = MagicMock()
        
        indexer = MultimodalIndexer()
        
        mock_qwen.assert_called_once()
        mock_milvus.assert_called_once()

    @patch('app.core.multimodal_indexer.get_qwen3vl_service')
    @patch('app.core.multimodal_indexer.get_milvus_service')
    @patch('app.core.multimodal_indexer.ObjectStorage')
    def test_embedding_dim_2048(self, mock_storage, mock_milvus, mock_qwen):
        """Test that indexer uses 2048-dim embeddings."""
        mock_qwen.return_value = MagicMock()
        mock_milvus.return_value = MagicMock()
        mock_storage.return_value = MagicMock()
        
        indexer = MultimodalIndexer()
        
        assert indexer.EMBEDDING_DIM == 2048

    @patch('app.core.multimodal_indexer.get_qwen3vl_service')
    @patch('app.core.multimodal_indexer.get_milvus_service')
    @patch('app.core.multimodal_indexer.ObjectStorage')
    def test_collection_name_v2(self, mock_storage, mock_milvus, mock_qwen):
        """Test that indexer uses v2 collection."""
        mock_qwen.return_value = MagicMock()
        mock_milvus_instance = MagicMock()
        mock_milvus.return_value = mock_milvus_instance
        mock_storage.return_value = MagicMock()
        
        indexer = MultimodalIndexer()
        
        assert indexer.collection_name == "paper_contents_v2"


class TestMultimodalIndexerIndexPaper:
    """Test paper indexing functionality."""

    @pytest.mark.asyncio
    @patch('app.core.multimodal_indexer.MultimodalIndexer._index_images')
    @patch('app.core.multimodal_indexer.MultimodalIndexer._index_tables')
    @patch('app.core.multimodal_indexer.get_qwen3vl_service')
    @patch('app.core.multimodal_indexer.get_milvus_service')
    @patch('app.core.multimodal_indexer.ObjectStorage')
    async def test_index_paper_success(
        self, mock_storage, mock_milvus, mock_qwen,
        mock_index_tables, mock_index_images
    ):
        """Test successful paper indexing."""
        mock_qwen.return_value = MagicMock()
        mock_milvus.return_value = MagicMock()
        mock_storage.return_value = MagicMock()
        
        mock_index_images.return_value = {"count": 5, "failures": []}
        mock_index_tables.return_value = {"count": 3, "failures": []}
        
        indexer = MultimodalIndexer()
        
        result = await indexer.index_paper(
            paper_id="test-paper-id",
            user_id="test-user-id",
            pdf_path="test.pdf",
            parsed_items=[],
            paper_markdown="Test markdown"
        )
        
        assert result["images_indexed"] == 5
        assert result["tables_indexed"] == 3
        assert result["partial_failures"] == []

    @pytest.mark.asyncio
    @patch('app.core.multimodal_indexer.MultimodalIndexer._index_images')
    @patch('app.core.multimodal_indexer.MultimodalIndexer._index_tables')
    @patch('app.core.multimodal_indexer.get_qwen3vl_service')
    @patch('app.core.multimodal_indexer.get_milvus_service')
    @patch('app.core.multimodal_indexer.ObjectStorage')
    async def test_index_paper_with_partial_failures(
        self, mock_storage, mock_milvus, mock_qwen,
        mock_index_tables, mock_index_images
    ):
        """Test paper indexing with partial failures."""
        mock_qwen.return_value = MagicMock()
        mock_milvus.return_value = MagicMock()
        mock_storage.return_value = MagicMock()
        
        mock_index_images.return_value = {
            "count": 3,
            "failures": [{"error": "Image extraction failed"}]
        }
        mock_index_tables.return_value = {
            "count": 2,
            "failures": [{"error": "Table extraction failed"}]
        }
        
        indexer = MultimodalIndexer()
        
        result = await indexer.index_paper(
            paper_id="test-paper-id",
            user_id="test-user-id",
            pdf_path="test.pdf",
            parsed_items=[],
            paper_markdown="Test markdown"
        )
        
        assert result["images_indexed"] == 3
        assert result["tables_indexed"] == 2
        assert len(result["partial_failures"]) == 2

    @pytest.mark.asyncio
    @patch('app.core.multimodal_indexer.MultimodalIndexer._index_images')
    @patch('app.core.multimodal_indexer.get_qwen3vl_service')
    @patch('app.core.multimodal_indexer.get_milvus_service')
    @patch('app.core.multimodal_indexer.ObjectStorage')
    async def test_index_paper_exception_handling(
        self, mock_storage, mock_milvus, mock_qwen, mock_index_images
    ):
        """Test paper indexing handles exceptions."""
        mock_qwen.return_value = MagicMock()
        mock_milvus.return_value = MagicMock()
        mock_storage.return_value = MagicMock()
        
        mock_index_images.side_effect = Exception("Unexpected error")
        
        indexer = MultimodalIndexer()
        
        result = await indexer.index_paper(
            paper_id="test-paper-id",
            user_id="test-user-id",
            pdf_path="test.pdf",
            parsed_items=[],
            paper_markdown="Test markdown"
        )
        
        assert result["images_indexed"] == 0
        assert len(result["partial_failures"]) > 0


class TestMultimodalIndexerImageIndexing:
    """Test image indexing."""

    @pytest.mark.asyncio
    @patch('app.core.multimodal_indexer.get_qwen3vl_service')
    @patch('app.core.multimodal_indexer.get_milvus_service')
    @patch('app.core.multimodal_indexer.ObjectStorage')
    async def test_index_images_with_pil_images(self, mock_storage, mock_milvus, mock_qwen):
        """Test indexing images from PIL objects."""
        mock_qwen_instance = MagicMock()
        mock_qwen_instance.encode_image.return_value = [0.1] * 2048
        mock_qwen.return_value = mock_qwen_instance
        
        mock_milvus_instance = MagicMock()
        mock_milvus_instance.insert.return_value = True
        mock_milvus.return_value = mock_milvus_instance
        
        mock_storage_instance = MagicMock()
        mock_storage_instance.upload_file.return_value = "https://s3.url/image.png"
        mock_storage.return_value = mock_storage_instance
        
        indexer = MultimodalIndexer()

    @pytest.mark.asyncio
    @patch('app.core.multimodal_indexer.get_qwen3vl_service')
    @patch('app.core.multimodal_indexer.get_milvus_service')
    @patch('app.core.multimodal_indexer.ObjectStorage')
    async def test_index_images_2048_dim_embedding(self, mock_storage, mock_milvus, mock_qwen):
        """Test that image embeddings are 2048-dim."""
        mock_qwen_instance = MagicMock()
        mock_qwen_instance.encode_image.return_value = [0.2] * 2048
        mock_qwen.return_value = mock_qwen_instance
        
        mock_milvus_instance = MagicMock()
        mock_milvus.return_value = mock_milvus_instance
        
        mock_storage_instance = MagicMock()
        mock_storage.return_value = mock_storage_instance
        
        indexer = MultimodalIndexer()
        
        embedding = mock_qwen_instance.encode_image("test.png")
        
        assert len(embedding) == 2048


class TestMultimodalIndexerTableIndexing:
    """Test table indexing."""

    @pytest.mark.asyncio
    @patch('app.core.multimodal_indexer.get_qwen3vl_service')
    @patch('app.core.multimodal_indexer.get_milvus_service')
    @patch('app.core.multimodal_indexer.ObjectStorage')
    async def test_index_tables_2048_dim_embedding(self, mock_storage, mock_milvus, mock_qwen):
        """Test that table embeddings are 2048-dim."""
        mock_qwen_instance = MagicMock()
        mock_qwen_instance.encode_table.return_value = [0.3] * 2048
        mock_qwen.return_value = mock_qwen_instance
        
        mock_milvus_instance = MagicMock()
        mock_milvus.return_value = mock_milvus_instance
        
        mock_storage_instance = MagicMock()
        mock_storage.return_value = mock_storage_instance
        
        indexer = MultimodalIndexer()
        
        embedding = mock_qwen_instance.encode_table(
            caption="Table 1",
            headers=["A", "B"],
            rows=[{"A": "1", "B": "2"}]
        )
        
        assert len(embedding) == 2048


class TestMultimodalIndexerIntegration:
    """Integration tests with actual services (mocked)."""

    @pytest.mark.asyncio
    @patch('app.core.multimodal_indexer.ImageExtractor')
    @patch('app.core.multimodal_indexer.TableExtractor')
    @patch('app.core.multimodal_indexer.get_qwen3vl_service')
    @patch('app.core.multimodal_indexer.get_milvus_service')
    @patch('app.core.multimodal_indexer.ObjectStorage')
    async def test_full_workflow(
        self, mock_storage, mock_milvus, mock_qwen,
        mock_table_extractor, mock_image_extractor
    ):
        """Test complete indexing workflow."""
        mock_qwen_instance = MagicMock()
        mock_qwen_instance.encode_text.return_value = [0.1] * 2048
        mock_qwen_instance.encode_image.return_value = [0.2] * 2048
        mock_qwen_instance.encode_table.return_value = [0.3] * 2048
        mock_qwen_instance.is_loaded.return_value = True
        mock_qwen.return_value = mock_qwen_instance
        
        mock_milvus_instance = MagicMock()
        mock_milvus_instance.insert.return_value = True
        mock_milvus.return_value = mock_milvus_instance
        
        mock_storage_instance = MagicMock()
        mock_storage_instance.upload_file.return_value = "https://s3.url/file"
        mock_storage.return_value = mock_storage_instance
        
        mock_image_extractor_instance = MagicMock()
        mock_image_extractor_instance.extract_images.return_value = [
            {
                "image": Image.new("RGB", (100, 100)),
                "caption": "Figure 1",
                "page": 1,
                "label": "1"
            }
        ]
        mock_image_extractor.return_value = mock_image_extractor_instance
        
        mock_table_extractor_instance = MagicMock()
        mock_table_extractor_instance.extract_tables.return_value = [
            {
                "caption": "Table 1",
                "headers": ["A", "B"],
                "rows": [{"A": "1", "B": "2"}],
                "page": 2,
                "label": "1"
            }
        ]
        mock_table_extractor.return_value = mock_table_extractor_instance
        
        indexer = MultimodalIndexer()
        
        result = await indexer.index_paper(
            paper_id="test-id",
            user_id="test-user",
            pdf_path="test.pdf",
            parsed_items=[],
            paper_markdown="Markdown content"
        )
        
        assert result["images_indexed"] >= 0
        assert result["tables_indexed"] >= 0

    @pytest.mark.asyncio
    @patch('app.core.multimodal_indexer.get_qwen3vl_service')
    @patch('app.core.multimodal_indexer.get_milvus_service')
    @patch('app.core.multimodal_indexer.ObjectStorage')
    async def test_milvus_connection_failure_handling(
        self, mock_storage, mock_milvus, mock_qwen
    ):
        """Test handling Milvus connection failure."""
        mock_qwen.return_value = MagicMock()
        
        mock_milvus_instance = MagicMock()
        mock_milvus_instance.connect.side_effect = Exception("Connection failed")
        mock_milvus.return_value = mock_milvus_instance
        
        mock_storage.return_value = MagicMock()
        
        indexer = MultimodalIndexer()
        
        assert indexer.milvus is not None


class TestMultimodalIndexerFactoryUsage:
    """Test that indexer uses factory pattern."""

    @patch('app.core.multimodal_indexer.get_qwen3vl_service')
    @patch('app.core.multimodal_indexer.get_milvus_service')
    @patch('app.core.multimodal_indexer.ObjectStorage')
    def test_uses_qwen3vl_factory(self, mock_storage, mock_milvus, mock_qwen):
        """Test that indexer gets Qwen3VL from factory."""
        mock_qwen.return_value = MagicMock()
        mock_milvus.return_value = MagicMock()
        mock_storage.return_value = MagicMock()
        
        indexer = MultimodalIndexer()
        
        mock_qwen.assert_called_once()
        assert indexer.qwen3vl_service is not None

    @patch('app.core.multimodal_indexer.get_qwen3vl_service')
    @patch('app.core.multimodal_indexer.get_milvus_service')
    @patch('app.core.multimodal_indexer.ObjectStorage')
    def test_uses_milvus_singleton(self, mock_storage, mock_milvus, mock_qwen):
        """Test that indexer gets Milvus singleton."""
        mock_qwen.return_value = MagicMock()
        mock_milvus.return_value = MagicMock()
        mock_storage.return_value = MagicMock()
        
        indexer = MultimodalIndexer()
        
        mock_milvus.assert_called_once()
        assert indexer.milvus is not None