"""RAPTOR-lite recursive summary tree builder.

Builds a hierarchical summary tree for academic papers using:
- BGE-M3 embeddings for chunk vectors
- AgglomerativeClustering for hierarchical grouping
- LLM summaries at each tree level

Resource budgets:
- max_chunks: 2000 per paper
- max_depth: 3
- max_llm_calls: 100 per paper
- import_timeout: 600s
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

import structlog
import numpy as np

logger = structlog.get_logger()

# Resource budgets
MAX_CHUNKS_PER_PAPER = 2000
MAX_DEPTH = 3
MAX_LLM_CALLS_PER_PAPER = 100
IMPORT_TIMEOUT_SECONDS = 600
SILHOUETTE_THRESHOLD = 0.3
MAX_CLUSTERS_FINAL = 5


@dataclass(frozen=True)
class TreeNode:
    """A node in the RAPTOR summary tree."""
    node_id: str
    paper_id: str
    user_id: str
    level: int
    text: str
    embedding: list[float]
    children_ids: tuple[str, ...] = ()
    cluster_label: int = -1


@dataclass
class TreeBuildResult:
    """Result of building a RAPTOR tree for a single paper."""
    paper_id: str
    nodes: list[TreeNode]
    depth: int
    llm_calls_used: int
    build_time_ms: float
    error: str | None = None


@dataclass
class ResourceBudget:
    """Tracks resource consumption during tree building."""
    llm_calls: int = 0
    start_time: float = field(default_factory=time.monotonic)

    @property
    def elapsed_seconds(self) -> float:
        return time.monotonic() - self.start_time

    def can_continue(self) -> bool:
        if self.llm_calls >= MAX_LLM_CALLS_PER_PAPER:
            return False
        if self.elapsed_seconds >= IMPORT_TIMEOUT_SECONDS:
            return False
        return True


def _try_import_sklearn():
    """Lazy import sklearn to avoid import errors when not installed."""
    try:
        from sklearn.cluster import AgglomerativeClustering
        from sklearn.metrics import silhouette_score
        return AgglomerativeClustering, silhouette_score
    except ImportError:
        return None, None


def _cluster_chunks(
    embeddings: np.ndarray,
    *,
    distance_threshold: float = 0.5,
) -> tuple[list[int], float] | None:
    """Cluster embeddings using AgglomerativeClustering.

    Returns:
        Tuple of (labels, silhouette_score) or None if clustering fails.
    """
    AgglomerativeClustering, silhouette_fn = _try_import_sklearn()
    if AgglomerativeClustering is None:
        return None

    if len(embeddings) < 3:
        return None

    try:
        clustering = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=distance_threshold,
            metric="cosine",
            linkage="average",
        )
        labels = clustering.fit_predict(embeddings)

        n_clusters = len(set(labels))
        if n_clusters < 2 or n_clusters >= len(embeddings):
            return None

        sil_score = silhouette_fn(embeddings, labels, metric="cosine")
        if sil_score < SILHOUETTE_THRESHOLD:
            return None

        return labels.tolist(), float(sil_score)
    except Exception as exc:
        logger.debug("Clustering failed", error=str(exc))
        return None


async def _generate_cluster_summary(
    *,
    cluster_texts: list[str],
    paper_id: str,
    level: int,
    llm_client: Any,
    budget: ResourceBudget,
) -> str:
    """Generate an LLM summary for a cluster of text chunks."""
    if not budget.can_continue():
        return ""

    combined = "\n---\n".join(cluster_texts[:10])
    if len(combined) > 4000:
        combined = combined[:4000] + "..."

    prompt = (
        f"以下是一篇学术论文（{paper_id}）中同一主题的多个段落片段。"
        f"请用中文生成一个简洁的综合摘要（3-5句话），概括这些片段的核心内容。\n\n"
        f"段落：\n{combined}\n\n摘要："
    )

    try:
        budget.llm_calls += 1
        summary = await llm_client.simple_completion(
            prompt=prompt,
            temperature=0.3,
            max_tokens=300,
        )
        return str(summary or "").strip()
    except Exception as exc:
        logger.warning("Cluster summary generation failed", paper_id=paper_id, error=str(exc))
        return ""


def _build_tree_recursive(
    *,
    paper_id: str,
    user_id: str,
    chunks: list[dict[str, Any]],
    embeddings: np.ndarray,
    level: int,
    parent_id: str | None,
    nodes: list[TreeNode],
    budget: ResourceBudget,
) -> None:
    """Recursively build the summary tree (synchronous clustering part).

    This builds the tree structure. LLM summaries are added asynchronously.
    """
    if level >= MAX_DEPTH or len(chunks) <= MAX_CLUSTERS_FINAL:
        return
    if not budget.can_continue():
        return

    # Try clustering
    result = _cluster_chunks(embeddings)
    if result is None:
        return

    labels, sil_score = result
    n_clusters = len(set(labels))

    # Group chunks by cluster
    clusters: dict[int, list[int]] = {}
    for idx, label in enumerate(labels):
        clusters.setdefault(label, []).append(idx)

    # Create nodes for each cluster
    for cluster_id, chunk_indices in clusters.items():
        node_id = f"raptor-{paper_id}-L{level}-C{cluster_id}-{uuid4().hex[:8]}"
        cluster_embeddings = embeddings[chunk_indices]
        centroid = cluster_embeddings.mean(axis=0).tolist()

        node = TreeNode(
            node_id=node_id,
            paper_id=paper_id,
            user_id=user_id,
            level=level,
            text="",  # Will be filled by LLM summary
            embedding=centroid,
            children_ids=tuple(chunks[i].get("chunk_id", "") for i in chunk_indices),
            cluster_label=cluster_id,
        )
        nodes.append(node)

        # Recurse if we have enough chunks in this cluster
        if len(chunk_indices) > MAX_CLUSTERS_FINAL and level + 1 < MAX_DEPTH:
            sub_chunks = [chunks[i] for i in chunk_indices]
            sub_embeddings = cluster_embeddings
            _build_tree_recursive(
                paper_id=paper_id,
                user_id=user_id,
                chunks=sub_chunks,
                embeddings=sub_embeddings,
                level=level + 1,
                parent_id=node_id,
                nodes=nodes,
                budget=budget,
            )


class RaptorTreeBuilder:
    """Builds RAPTOR-lite recursive summary trees for academic papers."""

    def __init__(self, *, embedding_provider: Any, llm_client: Any):
        self._embedding_provider = embedding_provider
        self._llm_client = llm_client

    async def build_tree(
        self,
        *,
        paper_id: str,
        user_id: str,
        chunks: list[dict[str, Any]],
    ) -> TreeBuildResult:
        """Build a RAPTOR tree for a single paper.

        Args:
            paper_id: The paper ID
            user_id: The user ID for isolation
            chunks: List of chunk dicts with at least 'chunk_id' and 'text' keys

        Returns:
            TreeBuildResult with the tree nodes
        """
        start_time = time.monotonic()
        budget = ResourceBudget()

        # Enforce chunk limit
        if len(chunks) > MAX_CHUNKS_PER_PAPER:
            return TreeBuildResult(
                paper_id=paper_id,
                nodes=[],
                depth=0,
                llm_calls_used=0,
                build_time_ms=0,
                error=f"Too many chunks: {len(chunks)} > {MAX_CHUNKS_PER_PAPER}",
            )

        if not chunks:
            return TreeBuildResult(
                paper_id=paper_id,
                nodes=[],
                depth=0,
                llm_calls_used=0,
                build_time_ms=0,
                error="No chunks provided",
            )

        # Step 1: Generate embeddings
        texts = [str(chunk.get("text", ""))[:512] for chunk in chunks]
        try:
            embedding_vectors = self._embedding_provider.embed_texts(texts)
            embeddings = np.array(embedding_vectors, dtype=np.float32)
        except Exception as exc:
            build_time = (time.monotonic() - start_time) * 1000
            return TreeBuildResult(
                paper_id=paper_id,
                nodes=[],
                depth=0,
                llm_calls_used=0,
                build_time_ms=build_time,
                error=f"Embedding generation failed: {exc}",
            )

        # Step 2: Build tree structure (clustering)
        nodes: list[TreeNode] = []

        # Add leaf nodes (original chunks)
        for idx, chunk in enumerate(chunks):
            node = TreeNode(
                node_id=chunk.get("chunk_id", f"leaf-{paper_id}-{idx}"),
                paper_id=paper_id,
                user_id=user_id,
                level=0,
                text=str(chunk.get("text", "")),
                embedding=embeddings[idx].tolist(),
            )
            nodes.append(node)

        # Build higher levels
        _build_tree_recursive(
            paper_id=paper_id,
            user_id=user_id,
            chunks=chunks,
            embeddings=embeddings,
            level=1,
            parent_id=None,
            nodes=nodes,
            budget=budget,
        )

        # Step 3: Generate LLM summaries for non-leaf nodes
        for node in nodes:
            if node.level == 0:
                continue
            if not node.text:
                # Collect children texts
                children_texts = [
                    n.text for n in nodes
                    if n.node_id in node.children_ids and n.text
                ]
                if children_texts:
                    summary = await _generate_cluster_summary(
                        cluster_texts=children_texts,
                        paper_id=paper_id,
                        level=node.level,
                        llm_client=self._llm_client,
                        budget=budget,
                    )
                    # Create updated node with summary
                    idx = nodes.index(node)
                    nodes[idx] = TreeNode(
                        node_id=node.node_id,
                        paper_id=node.paper_id,
                        user_id=node.user_id,
                        level=node.level,
                        text=summary,
                        embedding=node.embedding,
                        children_ids=node.children_ids,
                        cluster_label=node.cluster_label,
                    )

            if not budget.can_continue():
                break

        depth = max((n.level for n in nodes), default=0) + 1
        build_time = (time.monotonic() - start_time) * 1000

        logger.info(
            "RAPTOR tree built",
            paper_id=paper_id,
            node_count=len(nodes),
            depth=depth,
            llm_calls=budget.llm_calls,
            build_time_ms=round(build_time, 1),
        )

        return TreeBuildResult(
            paper_id=paper_id,
            nodes=nodes,
            depth=depth,
            llm_calls_used=budget.llm_calls,
            build_time_ms=build_time,
        )
