"""Unit tests for IntentClassifier with hybrid matching.

Tests hybrid intent classification:
- Rule-based matching (high confidence)
- LLM fallback (low confidence)
- Clarification for ambiguous intents

Per D-22, D-23: 8 intents with hybrid matching strategy.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.core.intent_classifier import (
    IntentClassifier,
    IntentType,
    classify,
    RULE_HIGH_CONFIDENCE,
    RULE_LOW_CONFIDENCE,
    CLARIFICATION_THRESHOLD,
)


class TestIntentClassifierBasic:
    """Test basic IntentClassifier functionality."""

    @pytest.mark.asyncio
    async def test_classify_returns_intent_result(self):
        """Test 1: classify() returns correct intent for all 8 types"""
        classifier = IntentClassifier(use_llm=False)

        # Test each intent type - use queries that match INTENT_RULES in intent_classifier.py
        test_cases = [
            ("what is attention", IntentType.QUESTION.value),
            ("compare A and B", IntentType.COMPARE.value),
            ("summarize this paper", IntentType.SUMMARY.value),
            ("evolution of YOLO", IntentType.EVOLUTION.value),
            ("method of this paper", IntentType.METHOD.value),
            ("results of experiment", IntentType.RESULTS.value),
            ("code for implementation", IntentType.CODE.value),
            ("references of paper", IntentType.REFERENCES.value),
        ]

        for query, expected_intent in test_cases:
            result = await classifier.classify(query)
            assert result["intent"] == expected_intent
            assert "confidence" in result
            assert "needs_clarification" in result

    @pytest.mark.asyncio
    async def test_classify_uses_rules_when_confidence_high(self):
        """Test 2: classify() uses rules when confidence >= 0.7"""
        classifier = IntentClassifier(use_llm=False)

        result = await classifier.classify("compare ResNet and VGG")

        assert result["intent"] == IntentType.COMPARE.value
        assert result["confidence"] >= RULE_LOW_CONFIDENCE

    @pytest.mark.asyncio
    async def test_classify_fallback_to_llm(self):
        """Test 3: classify() falls back to LLM when confidence < 0.7"""
        classifier = IntentClassifier(use_llm=True)

        # Mock LLM client
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"primary_intent": "question", "confidence": 0.8}'
                )
            )
        ]
        mock_llm.chat_completion = AsyncMock(return_value=mock_response)

        with patch("app.utils.zhipu_client.get_llm_client", return_value=mock_llm):
            result = await classifier.classify("ambiguous query xyz123")

            # Should have called LLM
            assert mock_llm.chat_completion.called

    @pytest.mark.asyncio
    async def test_llm_classification_returns_intent_and_confidence(self):
        """Test 3: LLM classification returns intent + confidence"""
        classifier = IntentClassifier(use_llm=True)

        # Mock LLM client
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"primary_intent": "method", "confidence": 0.75}'
                )
            )
        ]
        mock_llm.chat_completion = AsyncMock(return_value=mock_response)

        with patch("app.utils.zhipu_client.get_llm_client", return_value=mock_llm):
            llm_results = await classifier._classify_with_llm("test query")

            assert len(llm_results) > 0
            assert llm_results[0]["intent"] == "method"
            assert llm_results[0]["confidence"] == 0.75
            assert llm_results[0]["source"] == "llm"


class TestIntentClassifierHybrid:
    """Test hybrid matching behavior."""

    @pytest.mark.asyncio
    async def test_rule_based_has_zero_latency(self):
        """Test 4: Rule-based detection has zero latency (< 10ms)"""
        import time

        classifier = IntentClassifier(use_llm=False)

        start = time.time()
        result = await classifier.classify("compare A and B")
        elapsed = (time.time() - start) * 1000  # Convert to ms

        assert elapsed < 10  # Should be < 10ms
        assert result["intent"] == IntentType.COMPARE.value

    @pytest.mark.asyncio
    async def test_confidence_estimation_keywords(self):
        """Test rule-based confidence for keyword matches"""
        classifier = IntentClassifier(use_llm=False)

        result = await classifier.classify("compare these papers")

        # Keywords should give high confidence
        assert result["confidence"] >= RULE_HIGH_CONFIDENCE

    @pytest.mark.asyncio
    async def test_confidence_estimation_patterns(self):
        """Test rule-based confidence for pattern matches"""
        classifier = IntentClassifier(use_llm=False)

        result = await classifier.classify("what is the method")

        # Patterns should give high confidence
        assert result["confidence"] >= RULE_HIGH_CONFIDENCE


class TestIntentClassifierClarification:
    """Test clarification logic for ambiguous intents."""

    @pytest.mark.asyncio
    async def test_needs_clarification_when_close_confidence(self):
        """Test clarification when top intents have close confidence"""
        classifier = IntentClassifier(use_llm=False)

        # Mock close confidence results
        mock_results = [
            {"intent": "question", "confidence": 0.5, "source": "rules"},
            {"intent": "method", "confidence": 0.48, "source": "rules"},
            {"intent": "summary", "confidence": 0.3, "source": "rules"},
        ]

        result = classifier._check_clarification(mock_results, mock_results[0])

        # Should need clarification (difference < CLARIFICATION_THRESHOLD)
        assert result["needs_clarification"] is True
        assert len(result["suggested_intents"]) >= 2

    @pytest.mark.asyncio
    async def test_no_clarification_when_clear_winner(self):
        """Test no clarification when one intent has much higher confidence"""
        classifier = IntentClassifier(use_llm=False)

        mock_results = [
            {"intent": "compare", "confidence": 0.9, "source": "rules"},
            {"intent": "question", "confidence": 0.3, "source": "rules"},
            {"intent": "summary", "confidence": 0.2, "source": "rules"},
        ]

        result = classifier._check_clarification(mock_results, mock_results[0])

        # Should not need clarification (difference > CLARIFICATION_THRESHOLD)
        assert result["needs_clarification"] is False


class TestIntentClassifierErrorHandling:
    """Test error handling in IntentClassifier."""

    @pytest.mark.asyncio
    async def test_llm_failure_falls_back_to_question(self):
        """Test LLM failure falls back to question intent"""
        classifier = IntentClassifier(use_llm=True)

        # Mock LLM client to raise exception
        mock_llm = MagicMock()
        mock_llm.chat_completion = AsyncMock(side_effect=Exception("LLM error"))

        with patch("app.utils.zhipu_client.get_llm_client", return_value=mock_llm):
            result = await classifier._classify_with_llm("test query")

            # Should fall back to question with medium confidence
            assert len(result) > 0
            assert result[0]["intent"] == "question"
            assert result[0]["confidence"] == 0.5

    @pytest.mark.asyncio
    async def test_malformed_llm_response_falls_back(self):
        """Test malformed LLM response falls back to question"""
        classifier = IntentClassifier(use_llm=True)

        # Mock LLM client with malformed response
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="invalid json"))]
        mock_llm.chat_completion = AsyncMock(return_value=mock_response)

        with patch("app.utils.zhipu_client.get_llm_client", return_value=mock_llm):
            result = await classifier._classify_with_llm("test query")

            # Should fall back to question
            assert len(result) > 0
            assert result[0]["intent"] == "question"


class TestConvenienceFunction:
    """Test convenience function for quick classification."""

    @pytest.mark.asyncio
    async def test_classify_function(self):
        """Test classify() convenience function"""
        result = await classify("compare A and B")

        assert "intent" in result
        assert "confidence" in result
        assert result["intent"] in [t.value for t in IntentType]
