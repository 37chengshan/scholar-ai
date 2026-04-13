# tests/unit/test_complexity_router.py
"""Complexity Router unit tests.

审查增强：边界测试、规则优先、fallback统一
"""

import pytest
from app.core.complexity_router import ComplexityRouter

@pytest.fixture
def router():
    return ComplexityRouter()

@pytest.fixture
def router_with_mock_llm():
    """带Mock LLM的路由器（用于测试LLM fallback）"""
    class MockLLMClient:
        async def chat_completion(self, messages, **kwargs):
            return type('Response', (), {
                'choices': [type('Choice', (), {
                    'message': type('Message', (), {
                        'content': '{"complexity": "complex", "reasoning": "测试分类"}'
                    })
                })]
            })()
    return ComplexityRouter(llm_client=MockLLMClient())

class TestComplexityRouterRuleMatch:
    """规则强命中测试（复杂规则优先）"""

    def test_complex_rule_priority_over_simple(self, router):
        """复杂规则优先匹配"""
        # 这个query既匹配"这篇论文"（simple）又匹配"比较"（complex）
        # 应该优先匹配complex规则
        result = router.route("这篇论文和那篇论文的比较分析")
        assert result["complexity"] == "complex"
        assert result["method"] == "rule"

    def test_simple_rule_match_definition(self, router):
        """规则强命中: 定义类问题（缩窄后）"""
        result = router.route("什么是注意力机制?")
        assert result["complexity"] == "simple"
        assert result["method"] == "rule"
        assert result["confidence"] >= 0.9

    def test_simple_rule_match_summary_only(self, router):
        """规则强命中: 仅摘要类问题（缩窄）"""
        # 只有明确摘要场景才匹配simple
        result = router.route("请摘要这篇论文的主要内容")
        assert result["complexity"] == "simple"
        assert result["method"] == "rule"

    def test_complex_rule_match_comparison(self, router):
        """规则强命中: 比较类问题"""
        result = router.route("比较这两篇论文的方法差异")
        assert result["complexity"] == "complex"
        assert result["method"] == "rule"

    def test_complex_rule_match_evolution(self, router):
        """规则强命中: 演进类问题"""
        result = router.route("YOLO从v1到v4的演进历程")
        assert result["complexity"] == "complex"
        assert result["method"] == "rule"

class TestComplexityRouterEdgeCases:
    """边界测试（审查新增）"""

    def test_empty_query_returns_default(self, router):
        """空query返回default兜底"""
        result = router.route("")
        assert result["method"] == "default"
        assert result["complexity"] == "simple"  # 安全兜底

    def test_very_long_query_handled(self, router):
        """超长query正常处理"""
        long_query = "什么是" + "x" * 10000  # 10KB query
        result = router.route(long_query)
        assert result["method"] in ["rule", "default"]

    def test_query_with_special_chars(self, router):
        """特殊字符query正常处理"""
        result = router.route("什么是\n\r\t注意力机制??")
        assert result["complexity"] == "simple"

    def test_no_rule_match_returns_default(self, router):
        """无规则命中时返回default（统一修正）"""
        result = router.route("随便聊聊天气")
        assert result["method"] == "default"  # 修正：统一为default
        assert result["complexity"] == "simple"  # 安全兜底

class TestComplexityRouterKeywordMatch:
    """关键词匹配测试"""

    def test_keyword_simple_match(self, router):
        """关键词匹配: 简单问题"""
        result = router.route("解释transformer的工作原理")
        assert result["complexity"] == "simple"
        assert result["method"] in ["rule", "default"]  # 无LLM时

    def test_keyword_complex_match(self, router):
        """关键词匹配: 复杂问题"""
        result = router.route("这几篇论文的优缺点分析")
        # 应该命中complex规则
        assert result["complexity"] == "complex"

class TestComplexityRouterLLMFallback:
    """LLM fallback测试（需要mock）"""

    @pytest.mark.asyncio
    async def test_llm_classify_returns_complex(self, router_with_mock_llm):
        """LLM分类返回complex"""
        # Use a query that doesn't match any rule to trigger LLM fallback
        result = await router_with_mock_llm.route_async("请深入分析这个问题")  # No rule match
        assert result["complexity"] == "complex"
        assert result["method"] in ["hybrid", "llm"]

    @pytest.mark.asyncio
    async def test_llm_timeout_fallback(self, router_with_mock_llm):
        """LLM超时fallback到keyword"""
        # Mock超时场景
        class TimeoutLLMClient:
            async def chat_completion(self, messages, **kwargs):
                raise TimeoutError("LLM timeout")

        router = ComplexityRouter(llm_client=TimeoutLLMClient())
        result = await router.route_async("一些模糊的问题")
        assert result["method"] == "default"  # fallback到default

    @pytest.mark.asyncio
    async def test_llm_dirty_json_fallback(self, router_with_mock_llm):
        """LLM返回脏JSON时fallback"""
        class DirtyLLMClient:
            async def chat_completion(self, messages, **kwargs):
                return type('Response', (), {
                    'choices': [type('Choice', (), {
                        'message': type('Message', (), {
                            'content': 'not valid json'  # 脏数据
                        })
                    })]
                })()

        router = ComplexityRouter(llm_client=DirtyLLMClient())
        result = await router.route_async("测试问题")
        assert result["method"] in ["default"]  # fallback