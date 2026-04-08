"""Unit tests for intent classification rules.

Tests intent detection for 8 query types:
- compare: Multi-paper comparison queries
- evolution: Evolution/development analysis queries
- summary: Paper summary requests
- question: Single-paper questions (default)
- method: Methodology-related queries
- results: Results/findings queries
- code: Code/implementation queries
- references: References/citations queries
"""

import pytest
from app.core.intent_rules import INTENT_RULES, detect_intent


class TestIntentClassification:
    """Test intent classification rules."""

    def test_compare_intent_detection(self):
        """Test 1: 'YOLOv3和YOLOv4的区别' returns 'compare'"""
        query = "YOLOv3和YOLOv4的区别"
        intent = detect_intent(query)
        assert intent == "compare"

    def test_evolution_intent_detection(self):
        """Test 2: '从YOLOv1到YOLOv4的演进' returns 'evolution'"""
        query = "从YOLOv1到YOLOv4的演进"
        intent = detect_intent(query)
        assert intent == "evolution"

    def test_summary_intent_detection(self):
        """Test 3: '总结一下这篇论文' returns 'summary'"""
        query = "总结一下这篇论文"
        intent = detect_intent(query)
        assert intent == "summary"

    def test_question_intent_detection(self):
        """Test 4: '什么是注意力机制' returns 'question' (default)"""
        query = "什么是注意力机制"
        intent = detect_intent(query)
        assert intent == "question"

    def test_method_intent_detection(self):
        """Test new intent: method queries"""
        assert detect_intent("论文使用的方法是什么") == "method"
        assert detect_intent("explain the methodology") == "method"
        assert detect_intent("what approach did they use") == "method"

    def test_results_intent_detection(self):
        """Test new intent: results queries"""
        assert detect_intent("实验结果怎么样") == "results"
        assert detect_intent("what are the findings") == "results"
        assert detect_intent("show me the outcomes") == "results"

    def test_code_intent_detection(self):
        """Test new intent: code queries"""
        assert detect_intent("有代码实现吗") == "code"
        assert detect_intent("show the code") == "code"
        assert detect_intent("implementation details") == "code"

    def test_references_intent_detection(self):
        """Test new intent: references queries"""
        assert detect_intent("列出参考文献") == "references"
        assert detect_intent("list citations") == "references"
        assert detect_intent("related work") == "references"

    def test_keyword_matching(self):
        """Test 5: Keywords match correctly for each intent"""
        # Test compare keywords
        assert detect_intent("对比一下ResNet和VGG") == "compare"
        assert detect_intent("比较两种方法") == "compare"
        assert detect_intent("A和B的差异") == "compare"

        # Test evolution keywords
        assert detect_intent("YOLO的发展历程") == "evolution"
        assert detect_intent("注意力机制的演进过程") == "evolution"

        # Test summary keywords
        assert detect_intent("主要贡献是什么") == "summary"
        assert detect_intent("核心思想") == "summary"

        # Test new intents
        assert detect_intent("methodology section") == "method"
        assert detect_intent("数据结果") == "results"
        assert detect_intent("代码开源") == "code"
        assert detect_intent("bibliography") == "references"

    def test_pattern_matching(self):
        """Test 6: Patterns match correctly for complex queries"""
        # Compare patterns
        assert detect_intent("比较ResNet与VGG的性能") == "compare"
        assert detect_intent("BERT vs GPT") == "compare"

        # Evolution patterns
        assert detect_intent("从Transformer到GPT的演变") == "evolution"

        # Summary patterns
        assert detect_intent("ResNet的主要贡献") == "summary"

        # New intent patterns
        assert detect_intent("how does the method work") == "method"
        assert detect_intent("what are the results") == "results"
        assert detect_intent("show the code") == "code"
        assert detect_intent("list references") == "references"

    def test_case_insensitive_matching(self):
        """Test 7: Case-insensitive matching works"""
        # English keywords
        assert detect_intent("COMPARE these papers") == "compare"
        assert detect_intent("Compare A and B") == "compare"
        assert detect_intent("COMPARISON of methods") == "compare"

        # Mixed case
        assert detect_intent("YOLOv3 VS YOLOv4") == "compare"
        assert detect_intent("ResNet VERSUS VGG") == "compare"

        # New intents
        assert detect_intent("METHODOLOGY section") == "method"
        assert detect_intent("RESULTS AND FINDINGS") == "results"
        assert detect_intent("SHOW THE CODE") == "code"
        assert detect_intent("REFERENCES list") == "references"


class TestIntentRulesStructure:
    """Test INTENT_RULES dict structure."""

    def test_intent_rules_has_eight_intents(self):
        """INTENT_RULES should have exactly 8 intents"""
        expected_intents = [
            "compare",
            "evolution",
            "summary",
            "question",
            "method",
            "results",
            "code",
            "references",
        ]
        assert set(INTENT_RULES.keys()) == set(expected_intents)

    def test_intent_rules_has_keywords(self):
        """Each intent (except question) should have keywords"""
        for intent in [
            "compare",
            "evolution",
            "summary",
            "method",
            "results",
            "code",
            "references",
        ]:
            assert "keywords" in INTENT_RULES[intent]
            assert isinstance(INTENT_RULES[intent]["keywords"], list)
            assert len(INTENT_RULES[intent]["keywords"]) > 0

    def test_intent_rules_has_patterns(self):
        """Each intent (except question) should have patterns"""
        for intent in [
            "compare",
            "evolution",
            "summary",
            "method",
            "results",
            "code",
            "references",
        ]:
            assert "patterns" in INTENT_RULES[intent]
            assert isinstance(INTENT_RULES[intent]["patterns"], list)

    def test_question_intent_is_default(self):
        """Question intent should have empty keywords/patterns"""
        assert INTENT_RULES["question"]["keywords"] == []
        assert INTENT_RULES["question"]["patterns"] == []
