"""Page clustering algorithm using sklearn for semantic similarity.

Provides:
- cluster_pages: Group search results by page semantic similarity

Uses AgglomerativeClustering with precomputed distance matrix
to cluster pages based on BGE-M3 embeddings.

Requirements:
- OPT-03: Page clustering with semantic similarity
"""

from typing import Any, Dict, List

import numpy as np
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics.pairwise import cosine_similarity

from app.core.embedding.factory import get_embedding_service
from app.utils.logger import logger


async def cluster_pages(
    results: List[Dict[str, Any]],
    threshold: float = 0.8
) -> Dict[int, List[Dict[str, Any]]]:
    """Cluster search results by page semantic similarity.

    Args:
        results: List of search results with content_data and page_num
        threshold: Similarity threshold for clustering (default 0.8)

    Returns:
        Dict mapping cluster_id to list of results in that cluster

    Example:
        >>> results = [
        ...     {"page_num": 1, "content_data": "Introduction"},
        ...     {"page_num": 2, "content_data": "Introduction continued"},
        ... ]
        >>> clusters = await cluster_pages(results)
        >>> len(clusters) >= 1
        True
    """
    # Handle edge cases
    if len(results) == 0:
        return {}

    # For small result sets (< 3), return single cluster
    # (clustering not meaningful with few samples)
    if len(results) < 3:
        logger.info(
            "Small result set, returning single cluster",
            result_count=len(results),
        )
        return {0: results}

    # Aggregate content by page
    # Combine multiple chunks from same page
    page_content: Dict[int, List[str]] = {}
    for r in results:
        page = r.get("page_num", 0)
        if page not in page_content:
            page_content[page] = []
        # Truncate content to 500 chars per chunk to avoid encoding huge texts
        content = r.get("content_data", "")
        page_content[page].append(content[:500] if content else "")

    # Check if we have enough unique pages for clustering
    if len(page_content) < 3:
        logger.info(
            "Few unique pages, returning single cluster",
            unique_pages=len(page_content),
        )
        return {0: results}

    # Encode pages through the unified embedding contract.
    embedding_service = get_embedding_service()
    pages = list(page_content.keys())
    page_texts = [" ".join(page_content[p]) for p in pages]

    try:
        embeddings = embedding_service.encode_text(page_texts)
    except Exception as e:
        logger.error(
            "Failed to encode pages for clustering",
            error=str(e),
            page_count=len(pages),
        )
        # Fallback: return single cluster
        return {0: results}

    # Compute similarity matrix
    embeddings_matrix = np.array(embeddings)
    similarity = cosine_similarity(embeddings_matrix)
    distance = 1 - similarity

    # Agglomerative clustering
    # distance_threshold: clusters form when distance < (1 - threshold)
    clustering = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=1 - threshold,
        metric="precomputed",
        linkage="average"
    )

    labels = clustering.fit_predict(distance)

    # Group results by cluster
    clusters: Dict[int, List[Dict[str, Any]]] = {}
    for page, label in zip(pages, labels):
        # Get all results from this page
        cluster_results = [r for r in results if r.get("page_num") == page]
        if label not in clusters:
            clusters[label] = []
        clusters[label].extend(cluster_results)

    logger.info(
        "Page clustering complete",
        num_pages=len(pages),
        num_clusters=len(clusters),
        threshold=threshold,
    )

    return clusters
