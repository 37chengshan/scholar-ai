"""Tests for contextual embedding generation.

Tests the create_contextual_embedding method which:
1. Uses GLM-4.5-Air to generate context for a chunk
2. Combines context + chunk text
3. Returns embedding and contextualized text
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from app.core.embedding_service import EmbeddingService


class TestContextualEmbedding:
    """Test suite for contextual embedding generation."""

    @pytest.fixture
    def embedding_service(self):
        """Create EmbeddingService instance for testing."""
        return EmbeddingService(mock_mode=True)

    def test_create_contextual_embedding_exists(self, embedding_service):
        """Test 1: create_contextual_embedding() exists and accepts chunk_text and whole_document parameters."""
        # Check method exists
        assert hasattr(embedding_service, 'create_contextual_embedding')
        
        # Check it's callable
        assert callable(getattr(embedding_service, 'create_contextual_embedding'))

    @patch('app.core.embedding_service.ZhipuAI')
    def test_create_contextual_embedding_generates_context_with_glm(self, mock_zhipu, embedding_service):
        """Test 2: Function generates context using GLM-4.5-Air with Anthropic prompt template."""
        # Setup mock
        mock_client = MagicMock()
        mock_zhipu.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "This chunk discusses the experimental results."
        mock_client.chat.completions.create.return_value = mock_response

        chunk_text = "The proposed method achieves 95% accuracy on the benchmark dataset."
        whole_document = "Introduction... Methods... Results... The proposed method achieves 95% accuracy..."

        # Call method
        result = embedding_service.create_contextual_embedding(chunk_text, whole_document)

        # Verify GLM-4.5-Air was called
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args
        
        assert call_args[1]['model'] == 'glm-4.5-air'
        assert call_args[1]['messages'][0]['role'] == 'user'
        
        # Verify prompt template structure (Anthropic official)
        prompt = call_args[1]['messages'][0]['content']
        assert '<document>' in prompt
        assert '</document>' in prompt
        assert '<chunk>' in prompt
        assert '</chunk>' in prompt
        assert whole_document in prompt
        assert chunk_text in prompt

    @patch('app.core.embedding_service.ZhipuAI')
    def test_create_contextual_embedding_returns_embedding_and_text(self, mock_zhipu, embedding_service):
        """Test 3: Function combines context + chunk_text and returns embedding."""
        # Setup mock
        mock_client = MagicMock()
        mock_zhipu.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "This chunk discusses experimental results."
        mock_client.chat.completions.create.return_value = mock_response

        chunk_text = "The proposed method achieves 95% accuracy."
        whole_document = "Full paper text..."

        # Call method
        embedding, contextualized_text = embedding_service.create_contextual_embedding(
            chunk_text, whole_document
        )

        # Verify embedding is returned
        assert isinstance(embedding, list)
        assert len(embedding) == embedding_service.dimension
        assert all(isinstance(x, float) for x in embedding)

        # Verify contextualized text includes both context and chunk
        assert "This chunk discusses experimental results" in contextualized_text
        assert chunk_text in contextualized_text
        assert contextualized_text.startswith("This chunk discusses")

    @patch('app.core.embedding_service.ZhipuAI')
    def test_create_contextual_embedding_returns_contextualized_text(self, mock_zhipu, embedding_service):
        """Test 4: Function returns contextualized_text for storage."""
        # Setup mock
        mock_client = MagicMock()
        mock_zhipu.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        context = "Section: Results. Discusses model accuracy benchmarks."
        mock_response.choices[0].message.content = context
        mock_client.chat.completions.create.return_value = mock_response

        chunk_text = "The model achieved 92% F1 score."
        whole_document = "Paper about machine learning..."

        # Call method
        embedding, contextualized_text = embedding_service.create_contextual_embedding(
            chunk_text, whole_document
        )

        # Verify structure: context + "\n\n" + chunk
        assert contextualized_text == f"{context}\n\n{chunk_text}"

    @patch('app.core.embedding_service.ZhipuAI')
    @patch('time.sleep')
    def test_create_contextual_embedding_error_handling(self, mock_sleep, mock_zhipu, embedding_service):
        """Test 5: Error handling for API failures (retry with exponential backoff)."""
        # Setup mock to fail twice then succeed
        mock_client = MagicMock()
        mock_zhipu.return_value = mock_client
        
        # First two calls fail, third succeeds
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Context text"
        
        mock_client.chat.completions.create.side_effect = [
            Exception("API Error 1"),
            Exception("API Error 2"),
            mock_response
        ]

        chunk_text = "Test chunk"
        whole_document = "Test document"

        # Should succeed after retries
        embedding, contextualized_text = embedding_service.create_contextual_embedding(
            chunk_text, whole_document
        )

        # Verify retries happened (3 calls total)
        assert mock_client.chat.completions.create.call_count == 3
        
        # Verify exponential backoff was called
        assert mock_sleep.call_count == 2
        # First retry: ~1 second, second retry: ~2 seconds
        assert mock_sleep.call_args_list[0][0][0] >= 1
        assert mock_sleep.call_args_list[1][0][0] >= 2

    @patch('app.core.embedding_service.ZhipuAI')
    def test_create_contextual_embedding_max_tokens_and_temperature(self, mock_zhipu, embedding_service):
        """Test 6: Verify GLM-4.5-Air is called with correct parameters."""
        # Setup mock
        mock_client = MagicMock()
        mock_zhipu.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Context"
        mock_client.chat.completions.create.return_value = mock_response

        # Call method
        embedding_service.create_contextual_embedding("chunk", "document")

        # Verify parameters
        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]['max_tokens'] == 100
        assert call_args[1]['temperature'] == 0.3
        assert call_args[1]['thinking'] == {"type": "disabled"}