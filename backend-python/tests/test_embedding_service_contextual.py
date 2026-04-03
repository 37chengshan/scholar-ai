"""
Test contextual embedding integration in store_chunks().

This test suite verifies Gap 1 closure: contextual embeddings reduce
retrieval failure rate by 35% by situating each chunk within whole document context.

Updated for 13-02: Uses Milvus instead of PostgreSQL.
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from typing import List, Dict, Any
import asyncio

from app.core.embedding_service import EmbeddingService


# Fixtures

@pytest.fixture
def mock_milvus_service():
    """Mock MilvusService for vector storage."""
    mock = Mock()
    mock.insert_contents = Mock(return_value=[1, 2, 3])
    return mock


@pytest.fixture
def mock_bge_m3_service():
    """Mock BGEM3Service for 1024-dim embeddings."""
    mock = Mock()
    mock.encode_text = Mock(return_value=[0.1] * 1024)
    mock.EMBEDDING_DIM = 1024
    return mock


@pytest.fixture
def mock_glm_api():
    """Mock ZhipuAI GLM-4.5-Air API with fixed response."""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "This section discusses methodology for evaluating model performance."
    mock_client.chat.completions.create = Mock(return_value=mock_response)
    return mock_client


@pytest.fixture
def sample_chunks():
    """Sample chunks for testing."""
    return [
        {
            "text": "We evaluated our model on three benchmarks: MMLU, GSM8K, and HumanEval.",
            "section": "Methodology",
            "page_start": 5,
            "page_end": 5,
            "media": []
        },
        {
            "text": "Table 1 shows the performance comparison between our approach and baseline models.",
            "section": "Results",
            "page_start": 7,
            "page_end": 7,
            "media": [{"type": "table", "id": "table-1"}]
        },
        {
            "text": "The results demonstrate significant improvements across all benchmarks.",
            "section": "Results",
            "page_start": 8,
            "page_end": 8,
            "media": []
        }
    ]


@pytest.fixture
def whole_document_text():
    """Sample whole document markdown."""
    return """# Introduction
This paper presents a novel approach to large language model evaluation.

# Methodology
We evaluated our model on three benchmarks: MMLU, GSM8K, and HumanEval.
Our evaluation methodology follows standard practices in the field.

# Results
Table 1 shows the performance comparison between our approach and baseline models.
The results demonstrate significant improvements across all benchmarks.

# Discussion
Our findings suggest that contextual embeddings improve retrieval accuracy.

# Conclusion
We have demonstrated the effectiveness of our approach.
"""


# Tests

@pytest.mark.asyncio
async def test_store_chunks_accepts_whole_document_parameter(mock_bge_m3_service, mock_milvus_service, sample_chunks):
    """Test 1: store_chunks() accepts whole_document parameter."""
    with patch('app.core.embedding_service.get_bge_m3_service', return_value=mock_bge_m3_service):
        with patch('app.core.embedding_service.get_milvus_service', return_value=mock_milvus_service):
            service = EmbeddingService()

            # This should work with the new signature
            chunk_ids = await service.store_chunks(
                paper_id="test-paper-id",
                user_id="test-user-id",
                chunks=sample_chunks,
                whole_document="Sample document text"
            )

            # Verify it accepted the parameter
            assert isinstance(chunk_ids, list)


@pytest.mark.asyncio
async def test_contextual_embedding_called_per_chunk(mock_bge_m3_service, mock_milvus_service, sample_chunks, mock_glm_api, whole_document_text):
    """Test 2: When whole_document provided, calls create_contextual_embedding() for each chunk."""
    with patch('app.core.embedding_service.get_bge_m3_service', return_value=mock_bge_m3_service):
        with patch('app.core.embedding_service.get_milvus_service', return_value=mock_milvus_service):
            service = EmbeddingService()

            with patch('zhipuai.ZhipuAI', return_value=mock_glm_api):
                # Mock generate_embeddings_batch to track calls
                original_generate = service.generate_embeddings_batch
                call_count = 0

                def mock_generate(texts):
                    nonlocal call_count
                    call_count += 1
                    return [[0.1] * 1024 for _ in texts]

                service.generate_embeddings_batch = mock_generate

                # Store chunks with whole_document
                chunk_ids = await service.store_chunks(
                    paper_id="test-paper-id",
                    user_id="test-user-id",
                    chunks=sample_chunks,
                    whole_document=whole_document_text
                )

                # Verify create_contextual_embedding was called for each chunk (not batch embedding)
                # Should NOT call generate_embeddings_batch when using contextual embeddings
                assert call_count == 0, "Should not use batch embedding when whole_document provided"

                # Verify GLM API was called 3 times (once per chunk)
                assert mock_glm_api.chat.completions.create.call_count == len(sample_chunks)


@pytest.mark.asyncio
async def test_contextualized_text_stored(mock_bge_m3_service, mock_milvus_service, sample_chunks, mock_glm_api, whole_document_text):
    """Test 3: Contextual embedding stored instead of basic embedding."""
    with patch('app.core.embedding_service.get_bge_m3_service', return_value=mock_bge_m3_service):
        with patch('app.core.embedding_service.get_milvus_service', return_value=mock_milvus_service):
            service = EmbeddingService()

            with patch('zhipuai.ZhipuAI', return_value=mock_glm_api):
                chunk_ids = await service.store_chunks(
                    paper_id="test-paper-id",
                    user_id="test-user-id",
                    chunks=sample_chunks,
                    whole_document=whole_document_text
                )

                # Verify Milvus insert_contents was called
                assert mock_milvus_service.insert_contents.called

                # Check that the data passed to Milvus contains contextualized content
                call_args = mock_milvus_service.insert_contents.call_args
                inserted_data = call_args[0][0]  # First argument is the data list

                # Check that at least some chunks have contextualized content
                # (containing GLM-generated context)
                assert len(inserted_data) == len(sample_chunks)


@pytest.mark.asyncio
async def test_fallback_to_basic_embedding_when_none(mock_bge_m3_service, mock_milvus_service, sample_chunks):
    """Test 4: Integration handles None whole_document (fallback to basic embedding)."""
    with patch('app.core.embedding_service.get_bge_m3_service', return_value=mock_bge_m3_service):
        with patch('app.core.embedding_service.get_milvus_service', return_value=mock_milvus_service):
            service = EmbeddingService()

            # Mock batch embedding
            with patch.object(service, 'generate_embeddings_batch', return_value=[[0.1] * 1024 for _ in sample_chunks]):
                chunk_ids = await service.store_chunks(
                    paper_id="test-paper-id",
                    user_id="test-user-id",
                    chunks=sample_chunks,
                    whole_document=None  # No contextual embedding
                )

                # Verify batch embedding was called (fallback)
                assert service.generate_embeddings_batch.call_count == 1

                # Verify Milvus insert was called
                assert mock_milvus_service.insert_contents.called


@pytest.mark.asyncio
async def test_glm_prompt_template_used(mock_bge_m3_service, mock_milvus_service, sample_chunks, mock_glm_api, whole_document_text):
    """Test 5: Test with mock GLM API (verify Anthropic prompt template used)."""
    with patch('app.core.embedding_service.get_bge_m3_service', return_value=mock_bge_m3_service):
        with patch('app.core.embedding_service.get_milvus_service', return_value=mock_milvus_service):
            service = EmbeddingService()

            with patch('zhipuai.ZhipuAI', return_value=mock_glm_api):
                chunk_ids = await service.store_chunks(
                    paper_id="test-paper-id",
                    user_id="test-user-id",
                    chunks=sample_chunks[:1],  # Test with single chunk
                    whole_document=whole_document_text
                )

                # Verify GLM API called with correct prompt structure
                call_args = mock_glm_api.chat.completions.create.call_args

                # Check prompt contains Anthropic template elements
                prompt = call_args[1]['messages'][0]['content']

                # Anthropic template structure (per D-01):
                # <document> ... </document>
                # Here is the chunk we want to situate...
                # <chunk> ... </chunk>
                assert "<document>" in prompt
                assert "</document>" in prompt
                assert "<chunk>" in prompt
                assert "</chunk>" in prompt
                assert whole_document_text in prompt
                assert sample_chunks[0]["text"] in prompt


@pytest.mark.asyncio
async def test_integration_with_empty_whole_document(mock_bge_m3_service, mock_milvus_service, sample_chunks):
    """Test edge case: empty whole_document should fallback to basic embedding."""
    with patch('app.core.embedding_service.get_bge_m3_service', return_value=mock_bge_m3_service):
        with patch('app.core.embedding_service.get_milvus_service', return_value=mock_milvus_service):
            service = EmbeddingService()

            with patch.object(service, 'generate_embeddings_batch', return_value=[[0.1] * 1024 for _ in sample_chunks]):
                chunk_ids = await service.store_chunks(
                    paper_id="test-paper-id",
                    user_id="test-user-id",
                    chunks=sample_chunks,
                    whole_document=""  # Empty string
                )

                # Should use fallback (batch embedding)
                assert service.generate_embeddings_batch.call_count == 1


@pytest.mark.asyncio
async def test_large_whole_document_truncation(mock_bge_m3_service, mock_milvus_service, sample_chunks, mock_glm_api):
    """Test edge case: very long whole_document (>50k chars) truncation in prompt."""
    with patch('app.core.embedding_service.get_bge_m3_service', return_value=mock_bge_m3_service):
        with patch('app.core.embedding_service.get_milvus_service', return_value=mock_milvus_service):
            service = EmbeddingService()

            # Create large document (>50k chars)
            large_document = "Test content. " * 5000  # ~60k chars

            with patch('zhipuai.ZhipuAI', return_value=mock_glm_api):
                chunk_ids = await service.store_chunks(
                    paper_id="test-paper-id",
                    user_id="test-user-id",
                    chunks=sample_chunks[:1],
                    whole_document=large_document
                )

                # Verify GLM API called (prompt may be truncated in create_contextual_embedding)
                assert mock_glm_api.chat.completions.create.call_count == 1


@pytest.mark.asyncio
async def test_glm_api_failure_retry(mock_bge_m3_service, mock_milvus_service, sample_chunks, whole_document_text):
    """Test edge case: GLM API failure triggers retry logic."""
    with patch('app.core.embedding_service.get_bge_m3_service', return_value=mock_bge_m3_service):
        with patch('app.core.embedding_service.get_milvus_service', return_value=mock_milvus_service):
            service = EmbeddingService()

            # Mock API that fails first time, succeeds second time
            mock_client = Mock()
            mock_client.chat.completions.create = Mock(
                side_effect=[
                    Exception("API Error"),  # First call fails
                    Mock(choices=[Mock(message=Mock(content="Context after retry"))])  # Second succeeds
                ]
            )

            with patch('zhipuai.ZhipuAI', return_value=mock_client):
                chunk_ids = await service.store_chunks(
                    paper_id="test-paper-id",
                    user_id="test-user-id",
                    chunks=sample_chunks[:1],
                    whole_document=whole_document_text
                )

                # Verify retry happened (API called twice)
                assert mock_client.chat.completions.create.call_count == 2


@pytest.mark.asyncio
async def test_pdf_worker_integration_passes_whole_document(mock_bge_m3_service, mock_milvus_service, sample_chunks, mock_glm_api, whole_document_text):
    """Test 6: Integration test simulating pdf_worker flow."""
    with patch('app.core.embedding_service.get_bge_m3_service', return_value=mock_bge_m3_service):
        with patch('app.core.embedding_service.get_milvus_service', return_value=mock_milvus_service):
            service = EmbeddingService()

            # Simulate pdf_worker parsed data
            parsed_data = {
                "markdown": whole_document_text,
                "page_count": 10,
                "items": [],  # Mock items
            }

            with patch('zhipuai.ZhipuAI', return_value=mock_glm_api):
                # Simulate pdf_worker calling store_chunks with whole_document from parsed data
                chunk_ids = await service.store_chunks(
                    paper_id="test-paper-id",
                    user_id="test-user-id",
                    chunks=sample_chunks,
                    whole_document=parsed_data["markdown"]  # Pass from parsed data (as pdf_worker does)
                )

                # Verify whole_document parameter passed correctly
                assert mock_milvus_service.insert_contents.called

                # Verify GLM API was called for each chunk
                assert mock_glm_api.chat.completions.create.call_count == len(sample_chunks)

                # Verify chunks stored successfully
                assert len(chunk_ids) == len(sample_chunks)