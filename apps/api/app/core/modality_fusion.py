"""Modality fusion module for multimodal search.

Provides:
- detect_intent: Query intent detection based on keywords
- weighted_rrf_fusion: Weighted Reciprocal Rank Fusion across modalities
- Keyword lists: IMAGE_KEYWORDS, TABLE_KEYWORDS
- Weight presets: WEIGHT_PRESETS for different intents

The fusion approach uses weighted RRF to combine results from text, image, and table modalities,
adjusting weights based on detected query intent.
"""

from typing import Any, Dict, List


# Keyword lists for intent detection (per D-08 in CONTEXT.md)
IMAGE_KEYWORDS = ["图表", "figure", "chart", "图像", "示意图", "流程图", "diagram"]
TABLE_KEYWORDS = ["表格", "table", "数据", "对比", "性能指标", "实验结果"]

# Weight presets for different intents (per D-07 in CONTEXT.md)
WEIGHT_PRESETS = {
    "default": {"text": 0.5, "image": 0.3, "table": 0.2},
    "image_weighted": {"text": 0.3, "image": 0.6, "table": 0.1},
    "table_weighted": {"text": 0.4, "table": 0.5, "image": 0.1},
}


def detect_intent(query: str) -> str:
    """Detect query intent based on keywords.

    Matches keywords to determine if query prefers image or table results.
    Returns "default" if no keywords matched.

    Args:
        query: Search query string

    Returns:
        Intent string: "image_weighted", "table_weighted", or "default"
    """
    query_lower = query.lower()

    # Check for image keywords first
    for kw in IMAGE_KEYWORDS:
        if kw in query_lower:
            return "image_weighted"

    # Check for table keywords
    for kw in TABLE_KEYWORDS:
        if kw in query_lower:
            return "table_weighted"

    # Default intent
    return "default"


def weighted_rrf_fusion(
    multimodal_results: Dict[str, List[Dict[str, Any]]],
    weights: Dict[str, float],
    k: int = 60,
) -> List[Dict[str, Any]]:
    """Weighted Reciprocal Rank Fusion across modalities.

    RRF formula: score = weight / (k + rank)
    Combined score for items appearing in multiple modalities.

    Args:
        multimodal_results: Dict mapping modality -> results list
            Each result should have: id, paper_id, page_num, content_data
        weights: Dict mapping modality -> weight (0.0-1.0)
        k: RRF constant (default 60, standard academic value)

    Returns:
        List of fused results sorted by RRF score descending
        Each result includes rrf_score and modality_ranks
    """
    # Map of result_id -> fused result
    fused_map: Dict[str, Dict[str, Any]] = {}

    # Process each modality
    for modality, results in multimodal_results.items():
        weight = weights.get(modality, 0.0)

        # Skip empty results
        if not results:
            continue

        # Process results (rank starts at 1)
        for rank, result in enumerate(results, start=1):
            # Create unique result ID
            result_id = f"{result['paper_id']}-{result.get('page_num', 0)}-{result['id']}"

            # Calculate RRF score contribution
            rrf_score = weight / (k + rank)

            # Initialize or update fused result
            if result_id not in fused_map:
                fused_map[result_id] = {
                    **result,
                    "rrf_score": 0.0,
                    "modality_ranks": {},
                }

            # Add RRF score and record rank
            fused_map[result_id]["rrf_score"] += rrf_score
            fused_map[result_id]["modality_ranks"][modality] = rank

    # Convert to list and sort by RRF score descending
    fused_results = list(fused_map.values())
    fused_results.sort(key=lambda x: x["rrf_score"], reverse=True)

    return fused_results