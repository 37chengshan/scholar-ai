"""Hybrid intent classifier with LLM fallback.

Per D-22: 8 intent types (question, compare, summary, evolution, method, results, code, references).
Per D-23: Hybrid matching - rule engine priority (zero latency), LLM fallback for low confidence.
"""

from enum import Enum
from typing import Any, Dict, List
import re
import json

from app.utils.logger import logger


class IntentType(Enum):
    """8 intent types per D-22."""
    QUESTION = "question"
    COMPARE = "compare"
    SUMMARY = "summary"
    EVOLUTION = "evolution"
    METHOD = "method"
    RESULTS = "results"
    CODE = "code"
    REFERENCES = "references"


INTENT_RULES: Dict[IntentType, Dict[str, List[str]]] = {
    IntentType.QUESTION: {
        "keywords": ["what", "how", "why", "explain", "define", "describe", "什么", "怎么", "为什么"],
        "patterns": [r"^(what|how|why|explain|define)\s+"],
    },
    IntentType.COMPARE: {
        "keywords": ["compare", "difference", "vs", "versus", "对比", "比较", "区别", "差异"],
        "patterns": [r"(.+)和(.+)的 (区别 | 差异 | 对比)", r"(.+)\s+vs\s+(.+)"],
    },
    IntentType.SUMMARY: {
        "keywords": ["summarize", "summary", "overview", "摘要", "总结", "概述"],
        "patterns": [r"summarize\s+", r"(总结 | 摘要 | 概述)(一下)?"],
    },
    IntentType.EVOLUTION: {
        "keywords": ["trend", "history", "development", "timeline", "evolution", "演进", "发展", "历史"],
        "patterns": [r"从 (.+) 到 (.+) 的 (发展 | 演进)", r"trend\s+of\s+"],
    },
    IntentType.METHOD: {
        "keywords": ["method", "methodology", "approach", "technique", "方法", "方法论", "技术"],
        "patterns": [r"(method|methodology|approach)\s+(of|for)"],
    },
    IntentType.RESULTS: {
        "keywords": ["results", "findings", "outcomes", "data", "结果", "发现", "数据"],
        "patterns": [r"(results|findings)\s+(of|from)"],
    },
    IntentType.CODE: {
        "keywords": ["code", "implementation", "algorithm", "script", "代码", "实现", "算法"],
        "patterns": [r"(code|implementation)\s+(for|of)", r"show\s+me\s+the\s+code"],
    },
    IntentType.REFERENCES: {
        "keywords": ["references", "citations", "bibliography", "参考文献", "引用", "相关工作"],
        "patterns": [r"(references|citations)\s+(of|for)"],
    },
}

RULE_HIGH_CONFIDENCE = 0.9
RULE_LOW_CONFIDENCE = 0.7
CLARIFICATION_THRESHOLD = 0.2


class IntentClassifier:
    """Hybrid intent classifier with rule + LLM matching."""
    
    def __init__(self, use_llm: bool = True):
        self.use_llm = use_llm
        self.llm_client = None
    
    async def classify(self, query: str) -> Dict[str, Any]:
        """Classify user query intent."""
        logger.info("Classifying intent", query=query[:100])
        
        # Rule-based classification
        rule_results = self._classify_with_rules(query)
        top_intent = max(rule_results, key=lambda x: x["confidence"])
        
        # If rule confidence is high, return immediately
        if top_intent["confidence"] >= RULE_LOW_CONFIDENCE:
            return self._check_clarification(rule_results, top_intent)
        
        # LLM fallback (if enabled)
        if self.use_llm:
            llm_result = await self._classify_with_llm(query)
            combined_results = self._combine_results(rule_results, llm_result)
            top_intent = max(combined_results, key=lambda x: x["confidence"])
            return self._check_clarification(combined_results, top_intent)
        
        return self._check_clarification(rule_results, top_intent)
    
    def _classify_with_rules(self, query: str) -> List[Dict[str, Any]]:
        """Rule-based classification."""
        query_lower = query.lower()
        results = []
        
        for intent_type, rules in INTENT_RULES.items():
            confidence = 0.0
            
            for keyword in rules["keywords"]:
                if keyword.lower() in query_lower:
                    confidence = RULE_HIGH_CONFIDENCE
                    break
            
            if confidence < RULE_HIGH_CONFIDENCE:
                for pattern in rules["patterns"]:
                    if re.search(pattern, query, re.IGNORECASE):
                        confidence = RULE_HIGH_CONFIDENCE
                        break
            
            results.append({"intent": intent_type.value, "confidence": confidence, "source": "rules"})
        
        return results
    
    async def _classify_with_llm(self, query: str) -> List[Dict[str, Any]]:
        """LLM fallback classification."""
        try:
            if not self.llm_client:
                from app.utils.zhipu_client import get_llm_client
                self.llm_client = get_llm_client()
            
            prompt = f"""Classify into one of 8 intents: question, compare, summary, evolution, method, results, code, references.
Query: {query}
Return JSON: {{"primary_intent": "intent_name", "confidence": 0.0-1.0, "alternative_intents": []}}"""
            
            response = await self.llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500, temperature=0.3,
            )
            
            content = response.choices[0].message.content.strip()
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            
            if json_start >= 0 and json_end > json_start:
                llm_result = json.loads(content[json_start:json_end])
                results = []
                primary = llm_result.get("primary_intent")
                if primary:
                    results.append({"intent": primary, "confidence": llm_result.get("confidence", 0.5), "source": "llm"})
                return results
            
            return [{"intent": "question", "confidence": 0.5, "source": "llm"}]
        except Exception as e:
            logger.error("LLM intent classification failed", error=str(e))
            return [{"intent": "question", "confidence": 0.5, "source": "llm"}]
    
    def _combine_results(self, rule_results, llm_results):
        """Combine rule and LLM results with weighted average."""
        intent_scores = {}
        for result in rule_results:
            intent = result["intent"]
            intent_scores[intent] = {"rule": result["confidence"], "llm": 0.0}
        for result in llm_results:
            intent = result["intent"]
            if intent not in intent_scores:
                intent_scores[intent] = {"rule": 0.0, "llm": 0.0}
            intent_scores[intent]["llm"] = max(intent_scores[intent]["llm"], result["confidence"])
        
        return [
            {"intent": intent, "confidence": scores["rule"] * 0.6 + scores["llm"] * 0.4}
            for intent, scores in intent_scores.items()
        ]
    
    def _check_clarification(self, all_results, top_intent):
        """Check if clarification needed."""
        sorted_results = sorted(all_results, key=lambda x: x["confidence"], reverse=True)
        top_3 = sorted_results[:3]
        
        needs_clarification = False
        if len(top_3) >= 2:
            diff = top_3[0]["confidence"] - top_3[1]["confidence"]
            if diff < CLARIFICATION_THRESHOLD:
                needs_clarification = True
        
        examples = {
            "question": "What is the main contribution?",
            "compare": "Compare X and Y",
            "summary": "Summarize this paper",
            "evolution": "Show the evolution of X",
            "method": "What method did they use?",
            "results": "What were the results?",
            "code": "Show me the code",
            "references": "List references",
        }
        
        return {
            "intent": top_intent["intent"],
            "confidence": top_intent["confidence"],
            "needs_clarification": needs_clarification,
            "suggested_intents": [
                {"intent": r["intent"], "confidence": r["confidence"], "example": examples.get(r["intent"], "")}
                for r in top_3
            ],
        }


async def classify(query: str) -> Dict[str, Any]:
    """Convenience function for quick classification."""
    classifier = IntentClassifier()
    return await classifier.classify(query)


__all__ = ["IntentClassifier", "IntentType", "classify", "INTENT_RULES", "CLARIFICATION_THRESHOLD"]
