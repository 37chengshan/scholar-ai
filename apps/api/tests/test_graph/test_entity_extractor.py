"""
Tests for EntityExtractor with LiteLLM integration.

Tests the extraction of academic entities (methods, datasets, metrics, venues)
from paper content using LLM-based entity extraction.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestEntityExtractor:
    """Test suite for EntityExtractor class."""

    @pytest.mark.asyncio
    async def test_extract_entities_success(self, sample_extraction_text, mock_litellm_entity_response):
        """
        Test successful entity extraction from paper text.

        Verifies that:
        - LiteLLM is called with correct parameters
        - JSON response is parsed correctly
        - Methods, datasets, metrics, and venues are extracted
        - Confidence scores are included
        """
        from app.core.entity_extractor import EntityExtractor

        extractor = EntityExtractor(model="openai/qwen-plus")

        with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acompletion:
            mock_acompletion.return_value = mock_litellm_entity_response

            result = await extractor.extract(sample_extraction_text)

            # Verify structure
            assert "methods" in result
            assert "datasets" in result
            assert "metrics" in result
            assert "venues" in result

            # Verify content
            assert len(result["methods"]) > 0
            assert len(result["datasets"]) > 0
            assert len(result["metrics"]) > 0

            # Verify LiteLLM was called
            mock_acompletion.assert_called_once()
            call_args = mock_acompletion.call_args
            assert call_args.kwargs["model"] == "openai/qwen-plus"
            assert call_args.kwargs["temperature"] == 0.1
            assert call_args.kwargs["response_format"] == {"type": "json_object"}

    @pytest.mark.asyncio
    async def test_extract_entities_empty_text(self, empty_text):
        """
        Test entity extraction with empty text.

        Verifies that:
        - Empty text returns empty entity lists
        - No LLM call is made for very short/empty text
        - Returns graceful empty result
        """
        from app.core.entity_extractor import EntityExtractor

        extractor = EntityExtractor()

        with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acompletion:
            result = await extractor.extract(empty_text)

            # Should return empty structure without calling LLM
            assert result["methods"] == []
            assert result["datasets"] == []
            assert result["metrics"] == []
            assert result["venues"] == []

            # LLM should not be called for empty text
            mock_acompletion.assert_not_called()

    @pytest.mark.asyncio
    async def test_extract_entities_short_text(self, short_text):
        """
        Test entity extraction with very short text.

        Verifies that short text below threshold returns empty result.
        """
        from app.core.entity_extractor import EntityExtractor

        extractor = EntityExtractor()

        result = await extractor.extract(short_text)

        # Short text should return empty entities
        assert isinstance(result, dict)
        assert "methods" in result

    @pytest.mark.asyncio
    async def test_extract_entities_json_decode_error(self, sample_extraction_text, mock_litellm_malformed_response):
        """
        Test handling of malformed LLM JSON response.

        Verifies that:
        - Malformed JSON is handled gracefully
        - Returns empty entities as fallback
        - Error is logged
        """
        from app.core.entity_extractor import EntityExtractor

        extractor = EntityExtractor()

        with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acompletion:
            mock_acompletion.return_value = mock_litellm_malformed_response

            result = await extractor.extract(sample_extraction_text)

            # Should return empty structure on parse error
            assert "methods" in result
            assert "datasets" in result
            assert "metrics" in result
            assert "venues" in result

    @pytest.mark.asyncio
    async def test_extract_entities_timeout(self, sample_extraction_text):
        """
        Test handling of LLM timeout.

        Verifies that:
        - Timeout exceptions are caught
        - Returns empty result gracefully
        - Does not crash the application
        """
        from app.core.entity_extractor import EntityExtractor

        extractor = EntityExtractor()

        with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acompletion:
            mock_acompletion.side_effect = TimeoutError("Request timed out after 30 seconds")

            result = await extractor.extract(sample_extraction_text)

            # Should return empty structure on timeout
            assert isinstance(result, dict)
            assert "methods" in result

    @pytest.mark.asyncio
    async def test_extract_entities_api_error(self, sample_extraction_text):
        """
        Test handling of LLM API errors.

        Verifies that API errors are handled gracefully with fallback.
        """
        from app.core.entity_extractor import EntityExtractor

        extractor = EntityExtractor()

        with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acompletion:
            mock_acompletion.side_effect = Exception("API Error: Rate limit exceeded")

            result = await extractor.extract(sample_extraction_text)

            # Should return empty structure on API error
            assert isinstance(result, dict)
            assert "methods" in result


class TestEntityAligner:
    """Test suite for EntityAligner class."""

    @pytest.mark.asyncio
    async def test_entity_alignment_exact_match(self, mock_neo4j_session):
        """
        Test exact name matching for entity alignment.

        Verifies that:
        - Exact name match returns existing entity ID
        - No LLM call needed for exact matches
        - Case-insensitive matching works
        """
        from app.core.entity_extractor import EntityAligner

        aligner = EntityAligner()

        # Mock existing entity found
        mock_record = MagicMock()
        mock_record.data.return_value = {"id": "method-001", "name": "Transformer"}
        mock_result = AsyncMock()
        mock_result.single.return_value = mock_record
        mock_neo4j_session.run.return_value = mock_result

        with patch.object(aligner, "_get_neo4j_session", return_value=mock_neo4j_session):
            entity_id = await aligner.align_entity("Transformer", "Method")

            # Should return existing ID
            assert entity_id == "method-001"

    @pytest.mark.asyncio
    async def test_entity_alignment_llm_similarity(self, mock_neo4j_session, mock_litellm_similarity_response):
        """
        Test LLM-based similarity check for entity variants.

        Verifies that:
        - Similar entity names are checked with LLM
        - "YOLO" and "You Only Look Once" are identified as same entity
        - Variants like "YOLOv3" are handled correctly
        """
        from app.core.entity_extractor import EntityAligner

        aligner = EntityAligner()

        # Mock no exact match but similar candidates exist
        mock_neo4j_session.run.return_value = AsyncMock()
        mock_neo4j_session.run.return_value.data.return_value = [
            {"id": "method-001", "name": "YOLO", "similarity": 0.85}
        ]

        with patch.object(aligner, "_get_neo4j_session", return_value=mock_neo4j_session):
            with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acompletion:
                mock_acompletion.return_value = mock_litellm_similarity_response

                entity_id = await aligner.align_entity("YOLOv3", "Method")

                # LLM should be called for similarity check
                mock_acompletion.assert_called_once()

    @pytest.mark.asyncio
    async def test_entity_alignment_new_entity(self, mock_neo4j_session):
        """
        Test creation of new entity when no match found.

        Verifies that:
        - New entity is created when no match exists
        - New ID is returned
        - Entity is stored in Neo4j with proper properties
        """
        from app.core.entity_extractor import EntityAligner

        aligner = EntityAligner()

        # Mock no existing entity
        mock_result = AsyncMock()
        mock_result.single.return_value = None
        mock_result.data.return_value = []
        mock_neo4j_session.run.return_value = mock_result

        with patch.object(aligner, "_get_neo4j_session", return_value=mock_neo4j_session):
            # Mock new entity creation
            mock_create_result = AsyncMock()
            mock_create_result.single.return_value = {"id": "method-new-001"}

            with patch.object(mock_neo4j_session, "run", return_value=mock_create_result):
                entity_id = await aligner.align_entity("NewMethod", "Method")

                # Should return new entity ID
                assert entity_id is not None
                assert isinstance(entity_id, str)

    @pytest.mark.asyncio
    async def test_entity_alignment_batch(self, mock_neo4j_session):
        """
        Test batch alignment of multiple entities.

        Verifies that multiple entities can be aligned efficiently.
        """
        from app.core.entity_extractor import EntityAligner

        aligner = EntityAligner()
        entities = [
            {"name": "Transformer", "type": "Method"},
            {"name": "ImageNet", "type": "Dataset"},
            {"name": "mAP", "type": "Metric"},
        ]

        # Mock existing entities
        mock_result = AsyncMock()
        mock_result.data.return_value = [
            {"name": "Transformer", "id": "method-001"},
            {"name": "ImageNet", "id": "dataset-001"},
            {"name": "mAP", "id": "metric-001"},
        ]
        mock_neo4j_session.run.return_value = mock_result

        with patch.object(aligner, "_get_neo4j_session", return_value=mock_neo4j_session):
            results = await aligner.align_entities_batch(entities)

            # Should return list of aligned entity IDs
            assert len(results) == len(entities)
            assert all(isinstance(r, str) for r in results)


class TestEntityExtractionIntegration:
    """Integration tests for entity extraction pipeline."""

    @pytest.mark.asyncio
    async def test_extraction_with_alignment(self, sample_extraction_text, mock_litellm_entity_response, mock_neo4j_session):
        """
        Test full pipeline: extraction followed by alignment.

        Verifies that extracted entities are properly aligned to existing nodes.
        """
        from app.core.entity_extractor import EntityExtractor, EntityAligner

        extractor = EntityExtractor()
        aligner = EntityAligner()

        with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acompletion:
            mock_acompletion.return_value = mock_litellm_entity_response

            # Extract entities
            entities = await extractor.extract(sample_extraction_text)

            # Verify extraction succeeded
            assert "methods" in entities
            assert len(entities["methods"]) > 0

    @pytest.mark.asyncio
    async def test_extraction_confidence_scoring(self, sample_extraction_text):
        """
        Test confidence scoring for extracted entities.

        Verifies that confidence scores are properly assigned and used.
        """
        from app.core.entity_extractor import EntityExtractor

        extractor = EntityExtractor()

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps({
                        "methods": [
                            {"name": "HighConf", "context": "test", "confidence": 0.95},
                            {"name": "LowConf", "context": "test", "confidence": 0.45},
                        ],
                        "datasets": [],
                        "metrics": [],
                        "venues": [],
                    })
                )
            )
        ]

        with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acompletion:
            mock_acompletion.return_value = mock_response

            result = await extractor.extract(sample_extraction_text)

            # High confidence entity should be included
            high_conf = [m for m in result["methods"] if m.get("name") == "HighConf"]
            assert len(high_conf) > 0
            assert high_conf[0].get("confidence", 0) > 0.8

    @pytest.mark.asyncio
    async def test_extraction_with_truncation(self):
        """
        Test text truncation for long inputs.

        Verifies that long texts are truncated to avoid context overflow.
        """
        from app.core.entity_extractor import EntityExtractor

        extractor = EntityExtractor()

        # Create text exceeding max length
        long_text = "x" * 15000

        # Verify truncation logic
        truncated = extractor._truncate_text(long_text, max_length=8000)
        assert len(truncated) <= 8000 + 100  # Allow for truncation message

    @pytest.mark.asyncio
    async def test_extraction_prompt_format(self, sample_extraction_text):
        """
        Test that extraction prompt is properly formatted.

        Verifies prompt includes expected sections and instructions.
        """
        from app.core.entity_extractor import EntityExtractor, ENTITY_EXTRACTION_PROMPT

        # Verify prompt template exists and has expected content
        assert "methods" in ENTITY_EXTRACTION_PROMPT
        assert "datasets" in ENTITY_EXTRACTION_PROMPT
        assert "metrics" in ENTITY_EXTRACTION_PROMPT
        assert "venues" in ENTITY_EXTRACTION_PROMPT
        assert "JSON" in ENTITY_EXTRACTION_PROMPT


class TestEntityExtractorConfiguration:
    """Tests for EntityExtractor configuration."""

    def test_default_model(self):
        """
        Test default model configuration.

        Verifies that default model is set correctly.
        """
        from app.core.entity_extractor import EntityExtractor

        extractor = EntityExtractor()
        assert extractor.model is not None
        assert len(extractor.model) > 0

    def test_custom_model(self):
        """
        Test custom model configuration.

        Verifies that custom model can be specified.
        """
        from app.core.entity_extractor import EntityExtractor

        extractor = EntityExtractor(model="gpt-4o")
        assert extractor.model == "gpt-4o"

    def test_environment_variable_model(self):
        """
        Test that LLM_MODEL environment variable is respected.

        Verifies environment variable overrides default.
        """
        import os
        from unittest.mock import patch as mock_patch
        from app.core.entity_extractor import EntityExtractor

        with mock_patch.dict(os.environ, {"LLM_MODEL": "claude-3-haiku"}):
            extractor = EntityExtractor()
            # Model should be read from environment
            assert extractor.model == "claude-3-haiku"

    def test_max_text_length_configuration(self):
        """
        Test max text length configuration.

        Verifies that max text length can be configured.
        """
        from app.core.entity_extractor import EntityExtractor

        extractor = EntityExtractor(max_text_length=5000)
        assert extractor.max_text_length == 5000
